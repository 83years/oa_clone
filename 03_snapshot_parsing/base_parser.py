#!/usr/bin/env python3
"""
Base parser class for OpenAlex data with PostgreSQL COPY support
"""
import json
import gzip
import psycopg2
from io import StringIO
import time
from datetime import datetime
import sys
from pathlib import Path

# Add parent directory to path for config imports
SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(PARENT_DIR))

from config import DB_CONFIG, BATCH_SIZE, PROGRESS_INTERVAL, LOG_DIR


class BaseParser:
    """Base class for all OpenAlex entity parsers"""

    def __init__(self, entity_name, input_file, line_limit=None):
        """
        Initialize parser

        Args:
            entity_name: Name of entity being parsed (e.g., 'concepts', 'authors')
            input_file: Path to .gz file
            line_limit: Optional limit on number of lines to process (for testing)
        """
        self.entity_name = entity_name
        self.input_file = input_file
        self.line_limit = line_limit
        self.stats = {
            'lines_read': 0,
            'records_parsed': 0,
            'records_written': 0,
            'errors': 0,
            'start_time': None,
            'end_time': None
        }
        self.error_log_path = f"{LOG_DIR}/parse_{entity_name}_errors.log"
        self.conn = None

    def connect_db(self):
        """Establish database connection"""
        if not self.conn:
            self.conn = psycopg2.connect(**DB_CONFIG)
            cursor = self.conn.cursor()
            # Disable FK checks for bulk loading
            cursor.execute("SET session_replication_role = replica;")
            self.conn.commit()
            cursor.close()

    def close_db(self):
        """Close database connection and re-enable constraints"""
        if self.conn:
            cursor = self.conn.cursor()
            cursor.execute("SET session_replication_role = default;")
            self.conn.commit()
            cursor.close()
            self.conn.close()
            self.conn = None

    def read_gz_stream(self):
        """
        Generator that yields parsed JSON objects from .gz file

        Yields:
            dict: Parsed JSON object
        """
        print(f"[{datetime.now()}] Reading {self.input_file}...")

        try:
            with gzip.open(self.input_file, 'rt', encoding='utf-8') as f:
                for i, line in enumerate(f, 1):
                    self.stats['lines_read'] = i

                    # Progress reporting
                    if i % PROGRESS_INTERVAL == 0:
                        elapsed = time.time() - self.stats['start_time']
                        rate = i / elapsed
                        print(f"  [{datetime.now()}] Processed {i:,} lines | {rate:.0f} lines/sec")

                    # Check line limit
                    if self.line_limit and i > self.line_limit:
                        print(f"  [{datetime.now()}] Reached line limit of {self.line_limit:,}")
                        break

                    # Parse JSON
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        obj = json.loads(line)
                        yield obj
                    except json.JSONDecodeError as e:
                        self.stats['errors'] += 1
                        self.log_error(f"Line {i}: JSON decode error: {e}")
                        continue

        except Exception as e:
            self.log_error(f"Fatal error reading file: {e}")
            raise

    def write_with_copy(self, table_name, records, columns):
        """
        Bulk write using PostgreSQL COPY (fastest method)

        Args:
            table_name: Target table name
            records: List of dictionaries with data
            columns: List of column names in order
        """
        if not records:
            return

        # Create CSV buffer
        buffer = StringIO()
        for record in records:
            # Build row with proper NULL handling
            row = []
            for col in columns:
                value = record.get(col)
                if value is None:
                    row.append('\\N')  # PostgreSQL NULL marker
                elif isinstance(value, bool):
                    row.append('t' if value else 'f')
                elif isinstance(value, (int, float)):
                    row.append(str(value))
                elif isinstance(value, str):
                    # Escape special characters for COPY
                    value = value.replace('\\', '\\\\')
                    value = value.replace('\n', '\\n')
                    value = value.replace('\r', '\\r')
                    value = value.replace('\t', '\\t')
                    row.append(value)
                else:
                    row.append(str(value))

            buffer.write('\t'.join(row) + '\n')

        # Write to database using COPY
        buffer.seek(0)
        cursor = self.conn.cursor()
        try:
            cursor.copy_from(
                buffer,
                table_name,
                sep='\t',
                null='\\N',
                columns=columns
            )
            self.conn.commit()
            self.stats['records_written'] += len(records)
        except Exception as e:
            self.conn.rollback()
            self.log_error(f"COPY error for {table_name}: {e}")
            # Try again with execute_values as fallback
            self.write_with_execute_values(table_name, records, columns)
        finally:
            cursor.close()

    def write_with_execute_values(self, table_name, records, columns):
        """
        Fallback method using execute_values (slower but more forgiving)

        Args:
            table_name: Target table name
            records: List of dictionaries with data
            columns: List of column names in order
        """
        from psycopg2.extras import execute_values

        if not records:
            return

        # Convert to tuples
        data = []
        for record in records:
            row = tuple(record.get(col) for col in columns)
            data.append(row)

        cursor = self.conn.cursor()
        try:
            placeholders = ','.join(['%s'] * len(columns))
            sql = f"INSERT INTO {table_name} ({','.join(columns)}) VALUES %s ON CONFLICT DO NOTHING"
            execute_values(cursor, sql, data, page_size=BATCH_SIZE)
            self.conn.commit()
            self.stats['records_written'] += len(records)
        except Exception as e:
            self.conn.rollback()
            self.log_error(f"execute_values error for {table_name}: {e}")
            raise
        finally:
            cursor.close()

    def log_error(self, message):
        """Log error to file"""
        with open(self.error_log_path, 'a') as f:
            f.write(f"[{datetime.now()}] {message}\n")

    def print_stats(self):
        """Print parsing statistics"""
        elapsed = self.stats['end_time'] - self.stats['start_time']
        print(f"\n{'='*70}")
        print(f"✅ {self.entity_name.upper()} PARSING COMPLETE")
        print(f"{'='*70}")
        print(f"  Lines read:      {self.stats['lines_read']:,}")
        print(f"  Records parsed:  {self.stats['records_parsed']:,}")
        print(f"  Records written: {self.stats['records_written']:,}")
        print(f"  Errors:          {self.stats['errors']:,}")
        print(f"  Time elapsed:    {elapsed:.1f} seconds")
        print(f"  Parse rate:      {self.stats['lines_read']/elapsed:.0f} lines/sec")
        if self.stats['records_written'] > 0:
            print(f"  Write rate:      {self.stats['records_written']/elapsed:.0f} records/sec")
        print(f"{'='*70}\n")

    def clean_openalex_id(self, id_str):
        """Remove OpenAlex URL prefix from ID"""
        if not id_str:
            return None
        return str(id_str).replace('https://openalex.org/', '')

    def parse(self):
        """
        Main parse method - must be implemented by subclasses

        Should:
        1. Call read_gz_stream() to iterate through records
        2. Extract data into appropriate table structures
        3. Call write_with_copy() to bulk write data
        4. Return statistics
        """
        raise NotImplementedError("Subclasses must implement parse() method")

#!/usr/bin/env python3
"""
Apply OpenAlex Merged IDs to Critical Tables
Updates old/deprecated entity IDs to canonical IDs before building foreign keys
"""
import sys
import gzip
import csv
from pathlib import Path
from datetime import datetime
import psycopg2
from psycopg2.extras import execute_values
import argparse

SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PARENT_DIR))

from config import DB_CONFIG

MERGED_IDS_DIR = Path('/Volumes/OA_snapshot/24OCT2025/data/merged_ids')


class MergedIDsApplicator:
    """Applies merged IDs to critical relationship tables"""

    def __init__(self, test_mode=False):
        """
        Initialize merged IDs applicator

        Args:
            test_mode: Use test database (oadb2_test)
        """
        self.test_mode = test_mode
        db_config = DB_CONFIG.copy()
        db_config['database'] = 'OADB_test' if test_mode else 'OADB'

        self.conn = psycopg2.connect(**db_config)
        self.conn.autocommit = False
        self.cursor = self.conn.cursor()

        # Set up file logging
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        self.log_file = log_dir / 'apply_merged_ids.log'

        self.log(f"Connected to database: {db_config['database']}")
        self.log(f"Log file: {self.log_file}")

    def log(self, message):
        """Print timestamped message to console and file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] {message}"
        print(log_line)

        # Also write to file
        with open(self.log_file, 'a') as f:
            f.write(log_line + '\n')

    def load_merged_ids(self, entity_type):
        """
        Load all merged IDs for an entity type

        Args:
            entity_type: Entity type (authors, works, institutions, sources)

        Returns:
            dict: Mapping of old_id → canonical_id
        """
        entity_dir = MERGED_IDS_DIR / entity_type
        if not entity_dir.exists():
            self.log(f"⚠️  No merged_ids directory for {entity_type}")
            return {}

        merged_ids = {}
        csv_files = sorted(entity_dir.glob('*.csv.gz'))

        if not csv_files:
            self.log(f"⚠️  No merged_ids files found for {entity_type}")
            return {}

        self.log(f"Loading merged IDs for {entity_type} from {len(csv_files)} files...")

        for csv_file in csv_files:
            with gzip.open(csv_file, 'rt', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    old_id = row['id']
                    new_id = row['merge_into_id']
                    merged_ids[old_id] = new_id

        self.log(f"  Loaded {len(merged_ids):,} merged ID mappings for {entity_type}")
        return merged_ids

    def apply_merged_ids_to_table(self, table_name, column_name, merged_ids, entity_name):
        """
        Apply merged IDs to a specific table column

        Args:
            table_name: Table to update
            column_name: Column containing entity IDs
            merged_ids: Dictionary of old_id → new_id
            entity_name: Entity type name (for logging)

        Returns:
            int: Number of rows updated
        """
        if not merged_ids:
            self.log(f"  No merged IDs to apply for {entity_name} in {table_name}.{column_name}")
            return 0

        self.log(f"  Updating {table_name}.{column_name} with {len(merged_ids):,} {entity_name} merged IDs...")

        # Create temporary table with merged ID mappings
        temp_table = f"temp_merged_{entity_name}_{column_name}"

        self.cursor.execute(f"""
            CREATE TEMP TABLE {temp_table} (
                old_id TEXT,
                new_id TEXT
            )
        """)

        # Bulk insert merged ID mappings (in batches)
        batch_size = 50000
        mapping_tuples = list(merged_ids.items())

        for i in range(0, len(mapping_tuples), batch_size):
            batch = mapping_tuples[i:i+batch_size]
            execute_values(
                self.cursor,
                f"INSERT INTO {temp_table} (old_id, new_id) VALUES %s",
                batch
            )

        self.log(f"    Created temp table with {len(merged_ids):,} mappings")

        # Update table using temp table join
        update_query = f"""
            UPDATE {table_name}
            SET {column_name} = m.new_id
            FROM {temp_table} m
            WHERE {table_name}.{column_name} = m.old_id
        """

        self.cursor.execute(update_query)
        rows_updated = self.cursor.rowcount

        self.log(f"    ✅ Updated {rows_updated:,} rows in {table_name}.{column_name}")

        # Drop temp table
        self.cursor.execute(f"DROP TABLE {temp_table}")

        return rows_updated

    def apply_all_merged_ids(self):
        """Apply merged IDs to all critical relationship tables"""
        self.log("\n" + "="*70)
        self.log("APPLYING MERGED IDs TO CRITICAL TABLES")
        self.log("="*70 + "\n")

        total_updates = 0

        # Load all merged IDs
        self.log("STEP 1: Loading merged ID mappings...")
        authors_merged = self.load_merged_ids('authors')
        works_merged = self.load_merged_ids('works')
        institutions_merged = self.load_merged_ids('institutions')
        sources_merged = self.load_merged_ids('sources')

        self.log(f"\nTotal merged IDs loaded:")
        self.log(f"  Authors:      {len(authors_merged):,}")
        self.log(f"  Works:        {len(works_merged):,}")
        self.log(f"  Institutions: {len(institutions_merged):,}")
        self.log(f"  Sources:      {len(sources_merged):,}")

        # Apply to authorship table (CRITICAL for network analysis)
        self.log("\nSTEP 2: Updating authorship table...")
        total_updates += self.apply_merged_ids_to_table('authorship', 'author_id', authors_merged, 'authors')
        total_updates += self.apply_merged_ids_to_table('authorship', 'work_id', works_merged, 'works')
        total_updates += self.apply_merged_ids_to_table('authorship', 'institution_id', institutions_merged, 'institutions')
        self.conn.commit()
        self.log("  ✅ Authorship table updates committed")

        # Apply to citations_by_year table
        self.log("\nSTEP 3: Updating citations_by_year table...")
        total_updates += self.apply_merged_ids_to_table('citations_by_year', 'work_id', works_merged, 'works')
        self.conn.commit()
        self.log("  ✅ Citations_by_year table updates committed")

        # Apply to referenced_works table (both columns)
        self.log("\nSTEP 4: Updating referenced_works table...")
        total_updates += self.apply_merged_ids_to_table('referenced_works', 'work_id', works_merged, 'works')
        total_updates += self.apply_merged_ids_to_table('referenced_works', 'referenced_work_id', works_merged, 'works')
        self.conn.commit()
        self.log("  ✅ Referenced_works table updates committed")

        # Apply to related_works table (both columns)
        self.log("\nSTEP 5: Updating related_works table...")
        total_updates += self.apply_merged_ids_to_table('related_works', 'work_id', works_merged, 'works')
        total_updates += self.apply_merged_ids_to_table('related_works', 'related_work_id', works_merged, 'works')
        self.conn.commit()
        self.log("  ✅ Related_works table updates committed")

        # Summary
        self.log("\n" + "="*70)
        self.log(f"MERGED IDs APPLICATION COMPLETE")
        self.log(f"Total rows updated: {total_updates:,}")
        self.log("="*70 + "\n")

    def close(self):
        """Close database connection"""
        self.cursor.close()
        self.conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Apply OpenAlex Merged IDs')
    parser.add_argument('--test', action='store_true', help='Use test database (oadb2_test)')
    args = parser.parse_args()

    applicator = MergedIDsApplicator(test_mode=args.test)

    try:
        applicator.apply_all_merged_ids()
    except Exception as e:
        applicator.log(f"❌ Error: {e}")
        applicator.conn.rollback()
        sys.exit(1)
    finally:
        applicator.close()

#!/usr/bin/env python3
"""
Add Primary Keys to OpenAlex Database
Creates all primary key constraints on entity and relationship tables
"""
import sys
from pathlib import Path
from datetime import datetime
import psycopg2
import argparse

SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PARENT_DIR))

from config import DB_CONFIG


class PrimaryKeyBuilder:
    """Builds primary key constraints on all tables"""

    def __init__(self, test_mode=False):
        """
        Initialize primary key builder

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
        self.log_file = log_dir / 'add_primary_keys.log'

        self.log(f"Connected to database: {db_config['database']}")
        self.log(f"Log file: {self.log_file}")

        self.pk_stats = {'created': 0, 'skipped': 0, 'failed': 0}

    def log(self, message):
        """Print timestamped message to console and file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] {message}"
        print(log_line)

        # Also write to file
        with open(self.log_file, 'a') as f:
            f.write(log_line + '\n')

    def check_duplicates(self, table_name, columns):
        """
        Check for duplicate values in PK columns

        Args:
            table_name: Table name
            columns: List of column names (single or multiple)

        Returns:
            int: Count of duplicate groups
        """
        if isinstance(columns, str):
            columns = [columns]

        column_list = ', '.join(columns)

        query = f"""
            SELECT {column_list}, COUNT(*) as cnt
            FROM {table_name}
            GROUP BY {column_list}
            HAVING COUNT(*) > 1
        """

        self.cursor.execute(query)
        duplicates = self.cursor.fetchall()

        return len(duplicates)

    def add_primary_key(self, table_name, columns, constraint_name=None):
        """
        Add primary key constraint to table

        Args:
            table_name: Table name
            columns: Single column name or list of column names
            constraint_name: Optional constraint name (auto-generated if not provided)

        Returns:
            bool: True if successful, False otherwise
        """
        if isinstance(columns, str):
            columns = [columns]

        column_list = ', '.join(columns)

        if not constraint_name:
            constraint_name = f"{table_name}_pkey"

        self.log(f"  Adding PK to {table_name} ({column_list})...")

        # Check for duplicates
        duplicate_count = self.check_duplicates(table_name, columns)
        if duplicate_count > 0:
            self.log(f"    ⚠️  Found {duplicate_count:,} duplicate groups - CANNOT CREATE PK")
            self.pk_stats['failed'] += 1
            return False

        # Check if PK already exists
        self.cursor.execute("""
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = %s
              AND constraint_type = 'PRIMARY KEY'
        """, (table_name,))

        existing_pk = self.cursor.fetchone()
        if existing_pk:
            self.log(f"    ℹ️  Primary key already exists: {existing_pk[0]}")
            self.pk_stats['skipped'] += 1
            return True

        # Create primary key
        try:
            query = f"ALTER TABLE {table_name} ADD CONSTRAINT {constraint_name} PRIMARY KEY ({column_list})"
            self.cursor.execute(query)
            self.conn.commit()
            self.log(f"    ✅ Primary key created: {constraint_name}")
            self.pk_stats['created'] += 1
            return True

        except Exception as e:
            self.log(f"    ❌ Failed to create PK: {e}")
            self.conn.rollback()
            self.pk_stats['failed'] += 1
            return False

    def add_all_primary_keys(self, entity_filter=None):
        """
        Add all primary keys to database tables

        Args:
            entity_filter: Optional list of table names to filter. If None, process all tables.
        """
        self.log("\n" + "="*70)
        if entity_filter:
            self.log(f"ADDING PRIMARY KEYS TO SELECTED TABLES: {', '.join(entity_filter)}")
        else:
            self.log("ADDING PRIMARY KEYS TO ALL TABLES")
        self.log("="*70 + "\n")

        # Phase 1: Single-column primary keys (entity tables)
        self.log("PHASE 1: Single-column Primary Keys (Entity Tables)")
        single_column_pks = [
            ('works', 'work_id'),
            ('authors', 'author_id'),
            ('institutions', 'institution_id'),
            ('sources', 'source_id'),
            ('publishers', 'publisher_id'),
            ('funders', 'funder_id'),
            ('concepts', 'concept_id'),
            ('topics', 'topic_id'),
            ('institution_geo', 'institution_id'),
            ('search_metadata', 'search_id'),
        ]

        for table_name, column in single_column_pks:
            if entity_filter is None or table_name in entity_filter:
                self.add_primary_key(table_name, column)

        # Phase 2: Composite primary keys (relationship tables)
        self.log("\nPHASE 2: Composite Primary Keys (Relationship Tables)")
        composite_pks = [
            ('authorship', ['work_id', 'author_id', 'author_position']),
            ('work_topics', ['work_id', 'topic_id']),
            ('work_concepts', ['work_id', 'concept_id']),
            ('work_sources', ['work_id', 'source_id']),
            ('work_keywords', ['work_id', 'keyword']),
            ('work_funders', ['work_id', 'funder_id', 'award_id']),
            ('citations_by_year', ['work_id', 'year']),
            ('referenced_works', ['work_id', 'referenced_work_id']),
            ('related_works', ['work_id', 'related_work_id']),
            ('author_topics', ['author_id', 'topic_id']),
            ('author_concepts', ['author_id', 'concept_id']),
            ('author_institutions', ['author_id', 'institution_id']),
            ('authors_works_by_year', ['author_id', 'year']),
            ('source_publishers', ['source_id', 'publisher_id']),
            ('institution_hierarchy', ['parent_institution_id', 'child_institution_id', 'hierarchy_level']),
            ('topic_hierarchy', ['parent_topic_id', 'child_topic_id']),
        ]

        for table_name, columns in composite_pks:
            if entity_filter is None or table_name in entity_filter:
                self.add_primary_key(table_name, columns)

        # Summary
        self.log("\n" + "="*70)
        self.log(f"PRIMARY KEY CREATION COMPLETE")
        self.log(f"Created: {self.pk_stats['created']}")
        self.log(f"Skipped (already exists): {self.pk_stats['skipped']}")
        self.log(f"Failed: {self.pk_stats['failed']}")
        self.log("="*70 + "\n")

        if self.pk_stats['failed'] > 0:
            self.log("⚠️  Some primary keys failed to create - check for duplicates")
            return False

        return True

    def close(self):
        """Close database connection"""
        self.cursor.close()
        self.conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Add Primary Keys to Database')
    parser.add_argument('--test', action='store_true', help='Use test database (oadb2_test)')
    parser.add_argument('--entities', nargs='+', help='Specific table names to add primary keys to (e.g., --entities works authors authorship)')
    args = parser.parse_args()

    builder = PrimaryKeyBuilder(test_mode=args.test)

    try:
        success = builder.add_all_primary_keys(entity_filter=args.entities)
        sys.exit(0 if success else 1)
    except Exception as e:
        builder.log(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        builder.close()

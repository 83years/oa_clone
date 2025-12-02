#!/usr/bin/env python3
"""
Remove duplicate records from database tables.
Keeps one copy of each duplicate group based on specified strategy.
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


class DuplicateRemover:
    """Removes duplicate records from database tables"""

    def __init__(self, test_mode=False, dry_run=False):
        """
        Initialize duplicate remover

        Args:
            test_mode: Use test database
            dry_run: Only show what would be deleted, don't actually delete
        """
        self.test_mode = test_mode
        self.dry_run = dry_run
        db_config = DB_CONFIG.copy()
        db_config['database'] = 'oadbv5_test' if test_mode else 'oadbv5'

        self.conn = psycopg2.connect(**db_config)
        self.conn.autocommit = False
        self.cursor = self.conn.cursor()

        # Set up file logging
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        log_filename = 'remove_duplicates_dryrun.log' if dry_run else 'remove_duplicates.log'
        self.log_file = log_dir / log_filename

        self.log(f"Connected to database: {db_config['database']}")
        self.log(f"Log file: {self.log_file}")
        if dry_run:
            self.log("🔍 DRY RUN MODE - No data will be deleted")

        self.stats = {'tables_processed': 0, 'rows_deleted': 0}

    def log(self, message):
        """Print timestamped message to console and file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] {message}"
        print(log_line)

        # Also write to file
        with open(self.log_file, 'a') as f:
            f.write(log_line + '\n')

    def remove_duplicates(self, table_name, pk_columns, keep_strategy='first'):
        """
        Remove duplicates from a table

        Args:
            table_name: Table to clean
            pk_columns: Primary key columns (string or list)
            keep_strategy: Which row to keep ('first', 'last', 'max_ctid')

        Returns:
            int: Number of rows deleted
        """
        if isinstance(pk_columns, str):
            pk_columns = [pk_columns]

        column_list = ', '.join(pk_columns)

        self.log(f"\nProcessing {table_name} ({column_list})...")

        # Check if table has duplicates
        self.cursor.execute(f"""
            SELECT COUNT(*)
            FROM (
                SELECT {column_list}
                FROM {table_name}
                GROUP BY {column_list}
                HAVING COUNT(*) > 1
            ) dups
        """)

        duplicate_count = self.cursor.fetchone()[0]

        if duplicate_count == 0:
            self.log(f"  ✅ No duplicates found")
            return 0

        self.log(f"  ⚠️  Found {duplicate_count:,} duplicate groups")

        # Use PostgreSQL's ctid (physical row location) to identify and keep one row
        # We'll keep the row with the minimum ctid (first inserted)

        # Build the DELETE query using a CTE to identify duplicates to remove
        delete_query = f"""
            WITH duplicates AS (
                SELECT ctid,
                       ROW_NUMBER() OVER (PARTITION BY {column_list} ORDER BY ctid) AS rn
                FROM {table_name}
            )
            DELETE FROM {table_name}
            WHERE ctid IN (
                SELECT ctid FROM duplicates WHERE rn > 1
            )
        """

        if self.dry_run:
            # Count how many would be deleted
            count_query = f"""
                WITH duplicates AS (
                    SELECT ctid,
                           ROW_NUMBER() OVER (PARTITION BY {column_list} ORDER BY ctid) AS rn
                    FROM {table_name}
                )
                SELECT COUNT(*) FROM duplicates WHERE rn > 1
            """
            self.cursor.execute(count_query)
            would_delete = self.cursor.fetchone()[0]
            self.log(f"  🔍 Would delete {would_delete:,} duplicate rows")
            return would_delete
        else:
            # Actually delete
            self.cursor.execute(delete_query)
            deleted_count = self.cursor.rowcount
            self.conn.commit()
            self.log(f"  ✅ Deleted {deleted_count:,} duplicate rows")
            return deleted_count

    def remove_all_duplicates(self):
        """Remove duplicates from all tables"""
        self.log("\n" + "="*70)
        self.log("REMOVING DUPLICATES FROM ALL TABLES")
        if self.dry_run:
            self.log("🔍 DRY RUN MODE - No data will be deleted")
        self.log("="*70)

        # Define tables and their primary keys
        # Order matters: do entity tables first, then relationship tables
        tables_to_clean = [
            # Entity tables (single-column PKs)
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

            # Relationship tables (composite PKs)
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

        total_deleted = 0

        for table_name, pk_columns in tables_to_clean:
            try:
                deleted = self.remove_duplicates(table_name, pk_columns)
                total_deleted += deleted
                self.stats['tables_processed'] += 1
            except Exception as e:
                self.log(f"  ❌ Error processing {table_name}: {e}")
                self.conn.rollback()

        # Summary
        self.log("\n" + "="*70)
        self.log("DUPLICATE REMOVAL COMPLETE")
        self.log("="*70)
        self.log(f"Tables processed: {self.stats['tables_processed']}")

        if self.dry_run:
            self.log(f"Would delete: {total_deleted:,} duplicate rows")
            self.log("\n💡 Run without --dry-run to actually remove duplicates")
        else:
            self.log(f"Deleted: {total_deleted:,} duplicate rows")

        return total_deleted

    def close(self):
        """Close database connection"""
        self.cursor.close()
        self.conn.close()


    def get_table_definitions(self):
        """Return dictionary of all table definitions with their PKs"""
        return {
            # Entity tables (single-column PKs)
            'works': 'work_id',
            'authors': 'author_id',
            'institutions': 'institution_id',
            'sources': 'source_id',
            'publishers': 'publisher_id',
            'funders': 'funder_id',
            'concepts': 'concept_id',
            'topics': 'topic_id',
            'institution_geo': 'institution_id',
            'search_metadata': 'search_id',
            # Relationship tables (composite PKs)
            'authorship': ['work_id', 'author_id', 'author_position'],
            'work_topics': ['work_id', 'topic_id'],
            'work_concepts': ['work_id', 'concept_id'],
            'work_sources': ['work_id', 'source_id'],
            'work_keywords': ['work_id', 'keyword'],
            'work_funders': ['work_id', 'funder_id', 'award_id'],
            'citations_by_year': ['work_id', 'year'],
            'referenced_works': ['work_id', 'referenced_work_id'],
            'related_works': ['work_id', 'related_work_id'],
            'author_topics': ['author_id', 'topic_id'],
            'author_concepts': ['author_id', 'concept_id'],
            'author_institutions': ['author_id', 'institution_id'],
            'authors_works_by_year': ['author_id', 'year'],
            'source_publishers': ['source_id', 'publisher_id'],
            'institution_hierarchy': ['parent_institution_id', 'child_institution_id', 'hierarchy_level'],
            'topic_hierarchy': ['parent_topic_id', 'child_topic_id'],
        }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Remove duplicate records from database')
    parser.add_argument('--test', action='store_true', help='Use test database')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without actually deleting')
    parser.add_argument('--entities', type=str, nargs='+', help='Specific tables to process (space-separated list)')
    args = parser.parse_args()

    remover = DuplicateRemover(test_mode=args.test, dry_run=args.dry_run)

    try:
        if args.entities:
            # Get table definitions
            table_defs = remover.get_table_definitions()

            # Validate requested tables
            invalid_tables = [t for t in args.entities if t not in table_defs]
            if invalid_tables:
                remover.log(f"❌ Invalid table names: {', '.join(invalid_tables)}")
                remover.log(f"Available tables: {', '.join(sorted(table_defs.keys()))}")
                sys.exit(1)

            # Process only specified tables
            remover.log(f"Processing {len(args.entities)} specified table(s)")
            total_deleted = 0

            for table_name in args.entities:
                try:
                    pk_columns = table_defs[table_name]
                    deleted = remover.remove_duplicates(table_name, pk_columns)
                    total_deleted += deleted
                    remover.stats['tables_processed'] += 1
                except Exception as e:
                    remover.log(f"  ❌ Error processing {table_name}: {e}")
                    remover.conn.rollback()

            # Summary
            remover.log("\n" + "="*70)
            remover.log("DUPLICATE REMOVAL COMPLETE")
            remover.log("="*70)
            remover.log(f"Tables processed: {remover.stats['tables_processed']}")

            if remover.dry_run:
                remover.log(f"Would delete: {total_deleted:,} duplicate rows")
                remover.log("\n💡 Run without --dry-run to actually remove duplicates")
            else:
                remover.log(f"Deleted: {total_deleted:,} duplicate rows")
        else:
            # Process all tables
            remover.remove_all_duplicates()

    except Exception as e:
        remover.log(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        remover.close()

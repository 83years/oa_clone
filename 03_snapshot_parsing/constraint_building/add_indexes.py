#!/usr/bin/env python3
"""
Add Indexes to OpenAlex Database
Creates indexes on foreign key columns and common query fields
MUST be run BEFORE adding foreign key constraints for performance
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


class IndexBuilder:
    """Builds indexes on all critical columns"""

    def __init__(self, test_mode=False):
        """
        Initialize index builder

        Args:
            test_mode: Use test database (oadb2_test)
        """
        self.test_mode = test_mode
        db_config = DB_CONFIG.copy()
        db_config['database'] = 'oadbv5_test' if test_mode else 'oadbv5'

        self.conn = psycopg2.connect(**db_config)
        self.conn.autocommit = False
        self.cursor = self.conn.cursor()

        # Set up file logging
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        self.log_file = log_dir / 'add_indexes.log'

        self.log(f"Connected to database: {db_config['database']}")
        self.log(f"Log file: {self.log_file}")

        self.index_stats = {'created': 0, 'skipped': 0, 'failed': 0}

    def log(self, message):
        """Print timestamped message to console and file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] {message}"
        print(log_line)

        # Also write to file
        with open(self.log_file, 'a') as f:
            f.write(log_line + '\n')

    def create_index(self, table_name, column_name, index_name=None, index_type='btree'):
        """
        Create index on table column

        Args:
            table_name: Table name
            column_name: Column name (can be expression)
            index_name: Optional index name (auto-generated if not provided)
            index_type: Index type (btree, gin, gist, etc.)

        Returns:
            bool: True if successful, False otherwise
        """
        if not index_name:
            # Generate index name: idx_tablename_columnname
            clean_column = column_name.replace('(', '').replace(')', '').replace(' ', '_')
            index_name = f"idx_{table_name}_{clean_column}"

        # Check if index already exists
        self.cursor.execute("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = %s
              AND indexname = %s
        """, (table_name, index_name))

        if self.cursor.fetchone():
            self.log(f"  ℹ️  Index already exists: {index_name}")
            self.index_stats['skipped'] += 1
            return True

        self.log(f"  Creating index: {index_name} on {table_name}({column_name})...")

        try:
            if index_type.lower() == 'btree':
                query = f"CREATE INDEX {index_name} ON {table_name} ({column_name})"
            else:
                query = f"CREATE INDEX {index_name} ON {table_name} USING {index_type} ({column_name})"

            self.cursor.execute(query)
            self.conn.commit()
            self.log(f"    ✅ Index created")
            self.index_stats['created'] += 1
            return True

        except Exception as e:
            self.log(f"    ❌ Failed to create index: {e}")
            self.conn.rollback()
            self.index_stats['failed'] += 1
            return False

    def add_all_indexes(self):
        """Add all indexes to database tables"""
        self.log("\n" + "="*70)
        self.log("ADDING INDEXES TO ALL TABLES")
        self.log("="*70 + "\n")

        # Foreign key indexes (CRITICAL for FK constraint validation)
        self.log("PHASE 1: Foreign Key Column Indexes")

        fk_indexes = [
            # Authorship (most critical table)
            ('authorship', 'author_id'),
            ('authorship', 'work_id'),
            ('authorship', 'institution_id'),

            # Work relationships
            ('work_topics', 'work_id'),
            ('work_topics', 'topic_id'),
            ('work_concepts', 'work_id'),
            ('work_concepts', 'concept_id'),
            ('work_sources', 'work_id'),
            ('work_sources', 'source_id'),
            ('work_keywords', 'work_id'),
            ('work_funders', 'work_id'),
            ('work_funders', 'funder_id'),

            # Citations and references
            ('citations_by_year', 'work_id'),
            ('referenced_works', 'work_id'),
            ('referenced_works', 'referenced_work_id'),
            ('related_works', 'work_id'),
            ('related_works', 'related_work_id'),

            # Author relationships
            ('author_topics', 'author_id'),
            ('author_topics', 'topic_id'),
            ('author_concepts', 'author_id'),
            ('author_concepts', 'concept_id'),
            ('author_institutions', 'author_id'),
            ('author_institutions', 'institution_id'),
            ('authors_works_by_year', 'author_id'),
            ('author_name_variants', 'author_id'),

            # Source relationships
            ('source_publishers', 'source_id'),
            ('source_publishers', 'publisher_id'),

            # Institution relationships
            ('institution_geo', 'institution_id'),
            ('institution_hierarchy', 'parent_institution_id'),
            ('institution_hierarchy', 'child_institution_id'),

            # Topic hierarchy
            ('topic_hierarchy', 'parent_topic_id'),
            ('topic_hierarchy', 'child_topic_id'),
        ]

        for table_name, column_name in fk_indexes:
            self.create_index(table_name, column_name)

        # Common query indexes
        self.log("\nPHASE 2: Common Query Column Indexes")

        query_indexes = [
            # Works table
            ('works', 'publication_year'),
            ('works', 'publication_date'),
            ('works', 'works_type'),
            ('works', 'cited_by_count'),

            # Authors table
            ('authors', 'display_name'),
            ('authors', 'orcid'),
            ('authors', 'works_count'),
            ('authors', 'cited_by_count'),
            ('authors', 'last_known_institution'),

            # Institutions table
            ('institutions', 'display_name'),
            ('institutions', 'country_code'),
            ('institutions', 'institution_type'),

            # Sources table
            ('sources', 'display_name'),
            ('sources', 'issn_l'),
            ('sources', 'source_type'),

            # Topics and Concepts
            ('topics', 'display_name'),
            ('concepts', 'display_name'),

            # Authorship positions
            ('authorship', 'author_position'),
            ('authorship', 'is_corresponding'),
        ]

        for table_name, column_name in query_indexes:
            self.create_index(table_name, column_name)

        # Composite indexes for common queries
        self.log("\nPHASE 3: Composite Indexes for Common Queries")

        composite_indexes = [
            ('works', 'publication_year, cited_by_count', 'idx_works_year_citations'),
            ('authors', 'works_count, cited_by_count', 'idx_authors_productivity'),
            ('authorship', 'work_id, author_position', 'idx_authorship_work_position'),

            # Critical for authors_works_by_year rebuild
            ('authorship', 'author_id, author_position', 'idx_authorship_author_position'),
            ('authors_works_by_year', 'author_id, year', 'idx_awby_author_year'),

            # Useful for authors_works_by_year queries 
            ('authors_works_by_year', 'year', 'idx_awby_year'),  # Time-based filtering
        ]

        for table_name, columns, index_name in composite_indexes:
            self.create_index(table_name, columns, index_name)

        # Summary
        self.log("\n" + "="*70)
        self.log(f"INDEX CREATION COMPLETE")
        self.log(f"Created: {self.index_stats['created']}")
        self.log(f"Skipped (already exists): {self.index_stats['skipped']}")
        self.log(f"Failed: {self.index_stats['failed']}")
        self.log("="*70 + "\n")

        if self.index_stats['failed'] > 0:
            self.log("⚠️  Some indexes failed to create")
            return False

        return True

    def close(self):
        """Close database connection"""
        self.cursor.close()
        self.conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Add Indexes to Database')
    parser.add_argument('--test', action='store_true', help='Use test database (oadb2_test)')
    args = parser.parse_args()

    builder = IndexBuilder(test_mode=args.test)

    try:
        success = builder.add_all_indexes()
        sys.exit(0 if success else 1)
    except Exception as e:
        builder.log(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        builder.close()

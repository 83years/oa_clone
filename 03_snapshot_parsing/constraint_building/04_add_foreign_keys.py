#!/usr/bin/env python3
"""
Add Foreign Key Constraints to OpenAlex Database
Creates all FK constraints using NOT VALID for fast creation
Validation happens in separate validate_constraints.py script
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


class ForeignKeyBuilder:
    """Builds foreign key constraints on all relationship tables"""

    def __init__(self, test_mode=False):
        """
        Initialize foreign key builder

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
        self.log_file = log_dir / 'add_foreign_keys.log'

        self.log(f"Connected to database: {db_config['database']}")
        self.log(f"Log file: {self.log_file}")

        self.fk_stats = {'created': 0, 'skipped': 0, 'failed': 0}

    def log(self, message):
        """Print timestamped message to console and file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] {message}"
        print(log_line)

        # Also write to file
        with open(self.log_file, 'a') as f:
            f.write(log_line + '\n')

    def add_foreign_key(self, child_table, child_column, parent_table, parent_column,
                       constraint_name=None, on_delete='CASCADE'):
        """
        Add foreign key constraint

        Args:
            child_table: Child table name
            child_column: Child column name
            parent_table: Parent table name
            parent_column: Parent column name
            constraint_name: Optional constraint name
            on_delete: ON DELETE behavior (CASCADE, SET NULL, RESTRICT, etc.)

        Returns:
            bool: True if successful, False otherwise
        """
        if not constraint_name:
            constraint_name = f"fk_{child_table}_{child_column}_{parent_table}"

        # Check if FK already exists
        self.cursor.execute("""
            SELECT constraint_name
            FROM information_schema.table_constraints
            WHERE table_name = %s
              AND constraint_name = %s
              AND constraint_type = 'FOREIGN KEY'
        """, (child_table, constraint_name))

        if self.cursor.fetchone():
            self.log(f"  ℹ️  FK already exists: {constraint_name}")
            self.fk_stats['skipped'] += 1
            return True

        self.log(f"  Creating FK: {child_table}.{child_column} → {parent_table}.{parent_column}...")

        try:
            # Create FK with NOT VALID (fast creation, no immediate validation)
            query = f"""
                ALTER TABLE {child_table}
                ADD CONSTRAINT {constraint_name}
                FOREIGN KEY ({child_column})
                REFERENCES {parent_table}({parent_column})
                ON DELETE {on_delete}
                NOT VALID
            """

            self.cursor.execute(query)
            self.conn.commit()
            self.log(f"    ✅ FK created (NOT VALID)")
            self.fk_stats['created'] += 1
            return True

        except Exception as e:
            self.log(f"    ❌ Failed to create FK: {e}")
            self.conn.rollback()
            self.fk_stats['failed'] += 1
            return False

    def add_all_foreign_keys(self, scope='all'):
        """
        Add foreign key constraints

        Args:
            scope: Which FKs to create ('all', 'authorship', 'keywords')
        """
        self.log("\n" + "="*70)
        self.log(f"ADDING FOREIGN KEY CONSTRAINTS (NOT VALID) - SCOPE: {scope.upper()}")
        self.log("="*70 + "\n")

        # AUTHORSHIP-RELATED FOREIGN KEYS
        if scope in ['authorship', 'all']:
            self.log("PHASE 1: Authorship-Related Foreign Keys")

            # Authorship table (NO institution_id - that's in authorship_institutions!)
            self.log("\n  Authorship table...")
            self.add_foreign_key('authorship', 'work_id', 'works', 'work_id')
            self.add_foreign_key('authorship', 'author_id', 'authors', 'author_id')

            # Authorship institutions table (separate table for institution relationships)
            self.log("\n  Authorship institutions table...")
            self.add_foreign_key('authorship_institutions', 'work_id', 'works', 'work_id')
            self.add_foreign_key('authorship_institutions', 'author_id', 'authors', 'author_id')
            self.add_foreign_key('authorship_institutions', 'institution_id', 'institutions', 'institution_id')

            # Author relationship tables
            self.log("\n  Author relationship tables...")
            self.add_foreign_key('author_topics', 'author_id', 'authors', 'author_id')
            self.add_foreign_key('author_topics', 'topic_id', 'topics', 'topic_id')
            self.add_foreign_key('author_concepts', 'author_id', 'authors', 'author_id')
            self.add_foreign_key('author_concepts', 'concept_id', 'concepts', 'concept_id')
            self.add_foreign_key('author_institutions', 'author_id', 'authors', 'author_id')
            self.add_foreign_key('author_institutions', 'institution_id', 'institutions', 'institution_id')
            self.add_foreign_key('authors_works_by_year', 'author_id', 'authors', 'author_id')
            self.add_foreign_key('author_name_variants', 'author_id', 'authors', 'author_id')

        # KEYWORD-RELATED FOREIGN KEYS
        if scope in ['keywords', 'all']:
            self.log("\nPHASE 2: Keyword-Related Foreign Keys")
            self.add_foreign_key('work_keywords', 'work_id', 'works', 'work_id')

        # OTHER FOREIGN KEYS
        if scope == 'all':
            # Work relationship tables
            self.log("\nPHASE 3: Work Relationship Foreign Keys")
            self.add_foreign_key('work_topics', 'work_id', 'works', 'work_id')
            self.add_foreign_key('work_topics', 'topic_id', 'topics', 'topic_id')
            self.add_foreign_key('work_concepts', 'work_id', 'works', 'work_id')
            self.add_foreign_key('work_concepts', 'concept_id', 'concepts', 'concept_id')
            self.add_foreign_key('work_sources', 'work_id', 'works', 'work_id')
            self.add_foreign_key('work_sources', 'source_id', 'sources', 'source_id')
            self.add_foreign_key('work_funders', 'work_id', 'works', 'work_id')
            self.add_foreign_key('work_funders', 'funder_id', 'funders', 'funder_id')

            # Citations and references
            self.log("\nPHASE 4: Citation and Reference Foreign Keys")
            self.add_foreign_key('citations_by_year', 'work_id', 'works', 'work_id')
            self.add_foreign_key('referenced_works', 'work_id', 'works', 'work_id')
            self.add_foreign_key('referenced_works', 'referenced_work_id', 'works', 'work_id',
                               constraint_name='fk_referenced_works_referenced_id')
            self.add_foreign_key('related_works', 'work_id', 'works', 'work_id')
            self.add_foreign_key('related_works', 'related_work_id', 'works', 'work_id',
                               constraint_name='fk_related_works_related_id')

            # Source relationships
            self.log("\nPHASE 5: Source Relationship Foreign Keys")
            self.add_foreign_key('source_publishers', 'source_id', 'sources', 'source_id')
            self.add_foreign_key('source_publishers', 'publisher_id', 'publishers', 'publisher_id')

            # Institution relationships
            self.log("\nPHASE 6: Institution Relationship Foreign Keys")
            self.add_foreign_key('institution_geo', 'institution_id', 'institutions', 'institution_id')
            self.add_foreign_key('institution_hierarchy', 'parent_institution_id', 'institutions', 'institution_id',
                               constraint_name='fk_institution_hierarchy_parent')
            self.add_foreign_key('institution_hierarchy', 'child_institution_id', 'institutions', 'institution_id',
                               constraint_name='fk_institution_hierarchy_child')

            # Topic hierarchy
            self.log("\nPHASE 7: Topic Hierarchy Foreign Keys")
            self.add_foreign_key('topic_hierarchy', 'parent_topic_id', 'topics', 'topic_id',
                               constraint_name='fk_topic_hierarchy_parent')
            self.add_foreign_key('topic_hierarchy', 'child_topic_id', 'topics', 'topic_id',
                               constraint_name='fk_topic_hierarchy_child')

        # Summary
        self.log("\n" + "="*70)
        self.log(f"FOREIGN KEY CREATION COMPLETE")
        self.log(f"Created (NOT VALID): {self.fk_stats['created']}")
        self.log(f"Skipped (already exists): {self.fk_stats['skipped']}")
        self.log(f"Failed: {self.fk_stats['failed']}")
        self.log("\nℹ️  All FKs created with NOT VALID flag")
        self.log("ℹ️  Run validate_constraints.py to validate them")
        self.log("="*70 + "\n")

        if self.fk_stats['failed'] > 0:
            self.log("⚠️  Some foreign keys failed to create")
            return False

        return True

    def close(self):
        """Close database connection"""
        self.cursor.close()
        self.conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Add Foreign Keys to Database',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Scope options:
  all        - Create all foreign keys (default)
  authorship - Only create FKs for authorship, authors, works tables
  keywords   - Only create FKs for keyword/search tables

Examples:
  python add_foreign_keys.py --scope authorship    # Only authorship-related FKs
  python add_foreign_keys.py --scope keywords      # Only keyword-related FKs
  python add_foreign_keys.py --scope all           # All FKs
  python add_foreign_keys.py --test --scope authorship  # Authorship FKs on test DB
        """
    )
    parser.add_argument('--test', action='store_true', help='Use test database (oadbv5_test)')
    parser.add_argument('--scope',
                        choices=['all', 'authorship', 'keywords'],
                        default='all',
                        help='Which foreign keys to create (default: all)')
    args = parser.parse_args()

    builder = ForeignKeyBuilder(test_mode=args.test)

    try:
        success = builder.add_all_foreign_keys(scope=args.scope)
        sys.exit(0 if success else 1)
    except Exception as e:
        builder.log(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        builder.close()

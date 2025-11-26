#!/usr/bin/env python3
"""
Comprehensive verification script for OpenAlex database setup.

This script validates:
- Database connection
- Table structure
- Extensions
- Indexes and constraints
- Data integrity
- Performance settings
"""

import os
import sys
import psycopg2
from datetime import datetime

# Import centralized configuration
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

class DatabaseVerifier:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.checks_passed = 0
        self.checks_failed = 0
        self.warnings = 0

    def connect(self):
        """Establish database connection"""
        print(f"[{datetime.now()}] Connecting to database...")
        print(f"  Host: {config.DB_CONFIG['host']}")
        print(f"  Port: {config.DB_CONFIG['port']}")
        print(f"  Database: {config.DB_CONFIG['database']}")
        print(f"  User: {config.DB_CONFIG['user']}")

        try:
            self.conn = psycopg2.connect(**config.DB_CONFIG)
            self.cursor = self.conn.cursor()
            print("  ✅ Connection successful\n")
            self.checks_passed += 1
            return True
        except Exception as e:
            print(f"  ❌ Connection failed: {e}\n")
            self.checks_failed += 1
            return False

    def check_version(self):
        """Check PostgreSQL version"""
        print(f"[{datetime.now()}] Checking PostgreSQL version...")
        try:
            self.cursor.execute("SELECT version();")
            version = self.cursor.fetchone()[0]
            print(f"  {version}")

            if "PostgreSQL 16" in version:
                print("  ✅ PostgreSQL 16 detected\n")
                self.checks_passed += 1
            else:
                print("  ⚠️  Expected PostgreSQL 16\n")
                self.warnings += 1
        except Exception as e:
            print(f"  ❌ Error: {e}\n")
            self.checks_failed += 1

    def check_extensions(self):
        """Check required extensions"""
        print(f"[{datetime.now()}] Checking extensions...")

        required_extensions = ['pg_trgm', 'pg_stat_statements']

        for ext in required_extensions:
            try:
                self.cursor.execute("""
                    SELECT EXISTS(
                        SELECT 1 FROM pg_extension WHERE extname = %s
                    );
                """, (ext,))

                exists = self.cursor.fetchone()[0]
                if exists:
                    print(f"  ✅ {ext} installed")
                    self.checks_passed += 1
                else:
                    print(f"  ❌ {ext} not found")
                    self.checks_failed += 1
            except Exception as e:
                print(f"  ❌ Error checking {ext}: {e}")
                self.checks_failed += 1

        print()

    def check_tables(self):
        """Check table structure"""
        print(f"[{datetime.now()}] Checking tables...")

        expected_tables = [
            'topics', 'concepts', 'publishers', 'funders', 'sources', 'institutions',
            'institution_geo', 'authors', 'works', 'authorship', 'authorship_institutions',
            'work_topics', 'work_concepts', 'work_sources', 'citations_by_year',
            'referenced_works', 'related_works', 'work_funders', 'work_keywords',
            'author_topics', 'author_concepts', 'author_institutions', 'source_publishers',
            'institution_hierarchy', 'topic_hierarchy', 'alternate_ids', 'apc',
            'search_metadata', 'search_index', 'author_name_variants',
            'authors_works_by_year', 'data_modification_log'
        ]

        try:
            self.cursor.execute("""
                SELECT tablename
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY tablename;
            """)

            actual_tables = [row[0] for row in self.cursor.fetchall()]

            missing = set(expected_tables) - set(actual_tables)
            extra = set(actual_tables) - set(expected_tables)

            if not missing and not extra:
                print(f"  ✅ All {len(expected_tables)} tables present")
                self.checks_passed += 1
            else:
                if missing:
                    print(f"  ❌ Missing tables: {', '.join(missing)}")
                    self.checks_failed += 1
                if extra:
                    print(f"  ⚠️  Extra tables: {', '.join(extra)}")
                    self.warnings += 1

            # Show table counts
            print(f"  Total tables: {len(actual_tables)}")

        except Exception as e:
            print(f"  ❌ Error: {e}")
            self.checks_failed += 1

        print()

    def check_row_counts(self):
        """Check row counts in tables"""
        print(f"[{datetime.now()}] Checking table row counts...")

        try:
            self.cursor.execute("""
                SELECT
                    schemaname,
                    tablename,
                    n_live_tup as row_count
                FROM pg_stat_user_tables
                WHERE schemaname = 'public'
                ORDER BY n_live_tup DESC
                LIMIT 10;
            """)

            rows = self.cursor.fetchall()
            if rows:
                print("  Top 10 tables by row count:")
                for schema, table, count in rows:
                    print(f"    {table}: {count:,} rows")
                self.checks_passed += 1
            else:
                print("  ⚠️  No row count data available (might be empty database)")
                self.warnings += 1

        except Exception as e:
            print(f"  ❌ Error: {e}")
            self.checks_failed += 1

        print()

    def check_indexes(self):
        """Check indexes"""
        print(f"[{datetime.now()}] Checking indexes...")

        try:
            self.cursor.execute("""
                SELECT COUNT(*)
                FROM pg_indexes
                WHERE schemaname = 'public';
            """)

            index_count = self.cursor.fetchone()[0]
            print(f"  Total indexes: {index_count}")

            if index_count > 0:
                print(f"  ✅ Indexes present")
                self.checks_passed += 1
            else:
                print(f"  ⚠️  No indexes found (expected if constraints not yet added)")
                self.warnings += 1

        except Exception as e:
            print(f"  ❌ Error: {e}")
            self.checks_failed += 1

        print()

    def check_constraints(self):
        """Check constraints"""
        print(f"[{datetime.now()}] Checking constraints...")

        try:
            # Check primary keys
            self.cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.table_constraints
                WHERE constraint_schema = 'public'
                  AND constraint_type = 'PRIMARY KEY';
            """)
            pk_count = self.cursor.fetchone()[0]
            print(f"  Primary keys: {pk_count}")

            # Check foreign keys
            self.cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.table_constraints
                WHERE constraint_schema = 'public'
                  AND constraint_type = 'FOREIGN KEY';
            """)
            fk_count = self.cursor.fetchone()[0]
            print(f"  Foreign keys: {fk_count}")

            # Check unique constraints
            self.cursor.execute("""
                SELECT COUNT(*)
                FROM information_schema.table_constraints
                WHERE constraint_schema = 'public'
                  AND constraint_type = 'UNIQUE';
            """)
            unique_count = self.cursor.fetchone()[0]
            print(f"  Unique constraints: {unique_count}")

            if pk_count == 0 and fk_count == 0:
                print(f"  ⚠️  No constraints (expected for initial bulk loading)")
                self.warnings += 1
            else:
                print(f"  ✅ Constraints present")
                self.checks_passed += 1

        except Exception as e:
            print(f"  ❌ Error: {e}")
            self.checks_failed += 1

        print()

    def check_database_size(self):
        """Check database size"""
        print(f"[{datetime.now()}] Checking database size...")

        try:
            self.cursor.execute(f"""
                SELECT pg_size_pretty(pg_database_size('{config.DB_CONFIG['database']}'));
            """)
            size = self.cursor.fetchone()[0]
            print(f"  Database size: {size}")
            self.checks_passed += 1

        except Exception as e:
            print(f"  ❌ Error: {e}")
            self.checks_failed += 1

        print()

    def check_table_sizes(self):
        """Check table sizes"""
        print(f"[{datetime.now()}] Top 5 largest tables...")

        try:
            self.cursor.execute("""
                SELECT
                    tablename,
                    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
                    pg_total_relation_size(schemaname||'.'||tablename) AS bytes
                FROM pg_tables
                WHERE schemaname = 'public'
                ORDER BY bytes DESC
                LIMIT 5;
            """)

            rows = self.cursor.fetchall()
            if rows:
                for table, size, bytes_val in rows:
                    print(f"  {table}: {size}")
                self.checks_passed += 1
            else:
                print(f"  ⚠️  No size data available")
                self.warnings += 1

        except Exception as e:
            print(f"  ❌ Error: {e}")
            self.checks_failed += 1

        print()

    def check_configuration(self):
        """Check PostgreSQL configuration"""
        print(f"[{datetime.now()}] Checking PostgreSQL configuration...")

        config_checks = {
            'shared_buffers': '4GB',
            'work_mem': '256MB',
            'maintenance_work_mem': '2GB',
            'max_wal_size': '8GB',
        }

        for param, expected in config_checks.items():
            try:
                self.cursor.execute(f"SHOW {param};")
                actual = self.cursor.fetchone()[0]

                if actual == expected:
                    print(f"  ✅ {param}: {actual}")
                    self.checks_passed += 1
                else:
                    print(f"  ⚠️  {param}: {actual} (expected {expected})")
                    self.warnings += 1

            except Exception as e:
                print(f"  ❌ Error checking {param}: {e}")
                self.checks_failed += 1

        print()

    def check_connections(self):
        """Check active connections"""
        print(f"[{datetime.now()}] Checking active connections...")

        try:
            self.cursor.execute("""
                SELECT count(*)
                FROM pg_stat_activity
                WHERE datname = %s;
            """, (config.DB_CONFIG['database'],))

            connection_count = self.cursor.fetchone()[0]
            print(f"  Active connections: {connection_count}")

            if connection_count > 0:
                print(f"  ✅ Database is accessible")
                self.checks_passed += 1
            else:
                print(f"  ⚠️  No active connections")
                self.warnings += 1

        except Exception as e:
            print(f"  ❌ Error: {e}")
            self.checks_failed += 1

        print()

    def print_summary(self):
        """Print verification summary"""
        total_checks = self.checks_passed + self.checks_failed

        print("=" * 70)
        print("VERIFICATION SUMMARY")
        print("=" * 70)
        print(f"  ✅ Checks passed: {self.checks_passed}/{total_checks}")
        print(f"  ❌ Checks failed: {self.checks_failed}/{total_checks}")
        print(f"  ⚠️  Warnings: {self.warnings}")
        print("=" * 70)

        if self.checks_failed == 0:
            print("\n✅ Database setup verification PASSED")
            print("The database is properly configured and ready for use.\n")
            return True
        else:
            print("\n❌ Database setup verification FAILED")
            print("Please review the errors above and fix issues before proceeding.\n")
            return False

    def run_all_checks(self):
        """Run all verification checks"""
        print("=" * 70)
        print("OpenAlex Database Setup Verification")
        print("=" * 70)
        print()

        if not self.connect():
            return False

        self.check_version()
        self.check_extensions()
        self.check_tables()
        self.check_row_counts()
        self.check_indexes()
        self.check_constraints()
        self.check_database_size()
        self.check_table_sizes()
        self.check_configuration()
        self.check_connections()

        return self.print_summary()

    def cleanup(self):
        """Close database connections"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()


def main():
    """Main execution"""
    verifier = DatabaseVerifier()

    try:
        success = verifier.run_all_checks()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nVerification interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
    finally:
        verifier.cleanup()


if __name__ == "__main__":
    main()

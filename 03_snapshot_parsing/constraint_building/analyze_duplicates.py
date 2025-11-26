#!/usr/bin/env python3
"""
Comprehensive Duplicate Analysis for OpenAlex Database
Analyzes duplicate records and determines if they're identical or different data.
"""
import sys
import csv
import argparse
import traceback
from pathlib import Path
from datetime import datetime
import psycopg2

SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PARENT_DIR))

from config import DB_CONFIG


class DuplicateAnalyzer:
    """Analyzes duplicate records in database tables"""

    def __init__(self, test_mode=False):
        """
        Initialize duplicate analyzer

        Args:
            test_mode: Use test database
        """
        self.test_mode = test_mode
        db_config = DB_CONFIG.copy()
        if test_mode:
            # Append _test to existing database name
            base_db = db_config['database']
            db_config['database'] = f"{base_db}_test"

        self.conn = psycopg2.connect(**db_config)
        self.conn.autocommit = False
        self.cursor = self.conn.cursor()

        # Set up file logging
        log_dir = Path(__file__).parent / 'logs'
        log_dir.mkdir(exist_ok=True)
        self.log_file = log_dir / 'analyze_duplicates.log'

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

    def get_table_definitions(self):
        """Return dictionary of all table definitions with their PKs"""
        return {
            # Entity tables (single-column PKs)
            'works': ['work_id'],
            'authors': ['author_id'],
            'institutions': ['institution_id'],
            'sources': ['source_id'],
            'publishers': ['publisher_id'],
            'funders': ['funder_id'],
            'concepts': ['concept_id'],
            'topics': ['topic_id'],
            'institution_geo': ['institution_id'],
            'search_metadata': ['search_id'],

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
            'institution_hierarchy': [
                'parent_institution_id',
                'child_institution_id',
                'hierarchy_level'
            ],
            'topic_hierarchy': ['parent_topic_id', 'child_topic_id'],
        }

    def analyze_table_duplicates(self, table_name, pk_columns):
        """
        Comprehensive duplicate analysis for a table

        Args:
            table_name: Table to analyze
            pk_columns: List of primary key columns

        Returns:
            dict: Analysis results
        """
        column_list = ', '.join(pk_columns)
        self.log(f"\nAnalyzing {table_name} (PK: {column_list})...")

        # Count total rows
        self.cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_rows = self.cursor.fetchone()[0]

        if total_rows == 0:
            self.log(f"  ℹ️  Table is empty")
            return {
                'table': table_name,
                'pk_columns': pk_columns,
                'total_rows': 0,
                'duplicate_groups': 0,
                'duplicate_rows': 0,
                'identical_groups': 0,
                'different_groups': 0,
                'percentage': 0.0
            }

        # Count duplicate groups
        self.cursor.execute(f"""
            SELECT COUNT(*)
            FROM (
                SELECT {column_list}
                FROM {table_name}
                GROUP BY {column_list}
                HAVING COUNT(*) > 1
            ) dups
        """)
        duplicate_groups = self.cursor.fetchone()[0]

        if duplicate_groups == 0:
            self.log(f"  ✅ No duplicates found (Total rows: {total_rows:,})")
            return {
                'table': table_name,
                'pk_columns': pk_columns,
                'total_rows': total_rows,
                'duplicate_groups': 0,
                'duplicate_rows': 0,
                'identical_groups': 0,
                'different_groups': 0,
                'percentage': 0.0
            }

        # Count total duplicate rows (extras to remove)
        self.cursor.execute(f"""
            SELECT SUM(cnt - 1)
            FROM (
                SELECT {column_list}, COUNT(*) as cnt
                FROM {table_name}
                GROUP BY {column_list}
                HAVING COUNT(*) > 1
            ) dups
        """)
        result = self.cursor.fetchone()[0]
        duplicate_rows = result if result else 0

        # Check if duplicates are identical or different
        # Get all non-PK columns for comparison
        self.cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = %s
              AND column_name NOT IN %s
            ORDER BY ordinal_position
        """, (table_name, tuple(pk_columns)))

        other_columns = [row[0] for row in self.cursor.fetchall()]

        identical_groups = 0
        different_groups = 0

        if other_columns:
            # Use MD5 hash to check if duplicate rows are identical
            # Limit to first 20 columns for performance
            columns_to_hash = other_columns[:20]
            column_concat = ' || '.join([
                f"COALESCE({col}::text, '')" for col in columns_to_hash
            ])

            self.cursor.execute(f"""
                WITH row_hashes AS (
                    SELECT
                        {column_list},
                        MD5({column_concat}) as row_hash,
                        COUNT(*) OVER (PARTITION BY {column_list}) as dup_count
                    FROM {table_name}
                ),
                duplicate_groups AS (
                    SELECT
                        {column_list},
                        COUNT(DISTINCT row_hash) as distinct_hashes
                    FROM row_hashes
                    WHERE dup_count > 1
                    GROUP BY {column_list}
                )
                SELECT
                    COUNT(*) FILTER (
                        WHERE distinct_hashes = 1
                    ) as identical_groups,
                    COUNT(*) FILTER (
                        WHERE distinct_hashes > 1
                    ) as different_groups
                FROM duplicate_groups
            """)

            result = self.cursor.fetchone()
            identical_groups = result[0] if result[0] else 0
            different_groups = result[1] if result[1] else 0
        else:
            # No other columns, all duplicates must be identical
            identical_groups = duplicate_groups
            different_groups = 0

        percentage = (
            (duplicate_rows / total_rows * 100)
            if total_rows > 0 else 0.0
        )

        # Log results
        self.log(f"  📊 Total rows: {total_rows:,}")
        self.log(f"  ⚠️  Duplicate groups: {duplicate_groups:,}")
        self.log(
            f"  ⚠️  Duplicate rows (to remove): "
            f"{duplicate_rows:,} ({percentage:.3f}%)"
        )
        identical_pct = (identical_groups / duplicate_groups * 100)
        self.log(
            f"  ✅ Identical duplicates: "
            f"{identical_groups:,} ({identical_pct:.1f}%)"
        )

        if different_groups > 0:
            different_pct = (different_groups / duplicate_groups * 100)
            self.log(
                f"  🔴 Different data duplicates: "
                f"{different_groups:,} ({different_pct:.1f}%)"
            )
            self.log(f"     ⚠️  These require manual review!")

        return {
            'table': table_name,
            'pk_columns': pk_columns,
            'total_rows': total_rows,
            'duplicate_groups': duplicate_groups,
            'duplicate_rows': duplicate_rows,
            'identical_groups': identical_groups,
            'different_groups': different_groups,
            'percentage': percentage
        }

    def analyze_all_tables(self):
        """Analyze all tables for duplicates"""
        self.log("\n" + "="*70)
        self.log("COMPREHENSIVE DUPLICATE ANALYSIS - ALL TABLES")
        self.log("="*70)

        table_defs = self.get_table_definitions()
        results = []

        for table_name, pk_columns in table_defs.items():
            try:
                result = self.analyze_table_duplicates(table_name, pk_columns)
                results.append(result)
            except Exception as e:
                self.log(f"  ❌ Error analyzing {table_name}: {e}")
                traceback.print_exc()

        # Summary report
        self.log("\n" + "="*70)
        self.log("SUMMARY REPORT")
        self.log("="*70)

        tables_with_duplicates = [
            r for r in results if r['duplicate_groups'] > 0
        ]

        if tables_with_duplicates:
            self.log(
                f"\n⚠️  Found duplicates in "
                f"{len(tables_with_duplicates)} tables:\n"
            )

            # Header
            header = (
                f"{'Table':<25} {'Total Rows':<15} {'Dup Groups':<12} "
                f"{'Dup Rows':<12} {'Pct':<8} {'Identical':<10} "
                f"{'Different':<10}"
            )
            self.log(header)
            self.log("-"*100)

            for r in tables_with_duplicates:
                self.log(
                    f"{r['table']:<25} "
                    f"{r['total_rows']:>14,} "
                    f"{r['duplicate_groups']:>11,} "
                    f"{r['duplicate_rows']:>11,} "
                    f"{r['percentage']:>7.3f}% "
                    f"{r['identical_groups']:>9,} "
                    f"{r['different_groups']:>9,}"
                )

            total_dup_rows = sum(
                r['duplicate_rows'] for r in tables_with_duplicates
            )
            total_identical = sum(
                r['identical_groups'] for r in tables_with_duplicates
            )
            total_different = sum(
                r['different_groups'] for r in tables_with_duplicates
            )

            self.log(
                f"\n📊 Total duplicate rows to remove: {total_dup_rows:,}"
            )
            self.log(
                f"✅ Duplicate groups with identical data: "
                f"{total_identical:,}"
            )
            self.log(
                f"🔴 Duplicate groups with different data: "
                f"{total_different:,}"
            )

            if total_different > 0:
                self.log(
                    f"\n⚠️  WARNING: {total_different:,} duplicate groups "
                    f"have different data!"
                )
                self.log("   These require manual review before deletion.")
                self.log("   Options:")
                self.log("     1. Keep first inserted (lowest ctid)")
                self.log("     2. Keep last inserted (highest ctid)")
                self.log("     3. Manually review and merge data")

        else:
            self.log("\n✅ No duplicates found in any table")

        # Save detailed CSV report
        report_file = Path(__file__).parent / 'logs' / 'duplicate_analysis.csv'
        report_file.parent.mkdir(exist_ok=True)

        with open(report_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Table',
                'PK Columns',
                'Total Rows',
                'Duplicate Groups',
                'Duplicate Rows',
                'Percentage',
                'Identical Groups',
                'Different Groups',
                'Status'
            ])

            for r in results:
                pk_str = ', '.join(r['pk_columns'])
                status = 'No duplicates'
                if r['duplicate_groups'] > 0:
                    if r['different_groups'] > 0:
                        status = 'NEEDS REVIEW'
                    else:
                        status = 'Safe to delete'

                writer.writerow([
                    r['table'],
                    pk_str,
                    r['total_rows'],
                    r['duplicate_groups'],
                    r['duplicate_rows'],
                    f"{r['percentage']:.3f}%",
                    r['identical_groups'],
                    r['different_groups'],
                    status
                ])

        self.log(f"\n📄 Detailed CSV report saved to: {report_file}")

        return results

    def analyze_specific_tables(self, table_names):
        """
        Analyze specific tables for duplicates

        Args:
            table_names: List of table names to analyze
        """
        self.log("\n" + "="*70)
        self.log(f"ANALYZING SPECIFIC TABLES: {', '.join(table_names)}")
        self.log("="*70)

        table_defs = self.get_table_definitions()

        # Validate table names
        invalid_tables = [t for t in table_names if t not in table_defs]
        if invalid_tables:
            self.log(
                f"❌ Invalid table names: {', '.join(invalid_tables)}"
            )
            available = ', '.join(sorted(table_defs.keys()))
            self.log(f"Available tables: {available}")
            return []

        results = []
        for table_name in table_names:
            try:
                pk_columns = table_defs[table_name]
                result = self.analyze_table_duplicates(table_name, pk_columns)
                results.append(result)
            except Exception as e:
                self.log(f"  ❌ Error analyzing {table_name}: {e}")

        return results

    def close(self):
        """Close database connection"""
        self.cursor.close()
        self.conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description=(
            'Comprehensive duplicate analysis for OpenAlex database'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze all tables
  python analyze_duplicates.py

  # Analyze test database
  python analyze_duplicates.py --test

  # Analyze specific tables
  python analyze_duplicates.py --tables works authors authorship
        """
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Use test database'
    )
    parser.add_argument(
        '--tables',
        nargs='+',
        help='Specific tables to analyze (space-separated)'
    )
    args = parser.parse_args()

    analyzer = DuplicateAnalyzer(test_mode=args.test)

    try:
        if args.tables:
            analyzer.analyze_specific_tables(args.tables)
        else:
            analyzer.analyze_all_tables()
    except Exception as e:
        analyzer.log(f"❌ Error: {e}")
        traceback.print_exc()
        sys.exit(1)
    finally:
        analyzer.close()

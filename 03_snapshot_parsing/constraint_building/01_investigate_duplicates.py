#!/usr/bin/env python3
"""
Investigate duplicate records to understand why they exist.
Compares duplicate rows to see if they're identical or have different data.
"""
import sys
from pathlib import Path
from datetime import datetime
import psycopg2
import argparse
import json

SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PARENT_DIR))

from config import DB_CONFIG


class DuplicateInvestigator:
    """Investigates the nature of duplicate records"""

    def __init__(self, test_mode=False):
        """
        Initialize duplicate investigator

        Args:
            test_mode: Use test database
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
        self.log_file = log_dir / 'investigate_duplicates.log'

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

    def investigate_table(self, table_name, pk_column, sample_size=5):
        """
        Investigate duplicates in a table

        Args:
            table_name: Table to investigate
            pk_column: Primary key column (assumes single column for simplicity)
            sample_size: Number of duplicate IDs to examine in detail

        Returns:
            dict: Investigation results
        """
        self.log(f"\n{'='*70}")
        self.log(f"INVESTIGATING: {table_name}")
        self.log(f"{'='*70}")

        # Get sample of duplicate IDs
        self.cursor.execute(f"""
            SELECT {pk_column}, COUNT(*) as cnt
            FROM {table_name}
            GROUP BY {pk_column}
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC
            LIMIT {sample_size}
        """)

        duplicate_ids = self.cursor.fetchall()

        if not duplicate_ids:
            self.log("✅ No duplicates found")
            return {'has_duplicates': False}

        self.log(f"Found {len(duplicate_ids)} duplicate IDs to examine\n")

        # For each duplicate ID, get all rows and compare them
        identical_count = 0
        different_count = 0

        for dup_id, dup_count in duplicate_ids:
            self.log(f"Examining ID: {dup_id} ({dup_count} copies)")

            # Get all columns for this table
            self.cursor.execute(f"""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position
            """)
            columns = [row[0] for row in self.cursor.fetchall()]
            column_list = ', '.join(columns)

            # Get all rows for this duplicate ID
            self.cursor.execute(f"""
                SELECT {column_list}
                FROM {table_name}
                WHERE {pk_column} = %s
            """, (dup_id,))

            rows = self.cursor.fetchall()

            # Compare rows
            first_row = rows[0]
            all_identical = all(row == first_row for row in rows)

            if all_identical:
                self.log(f"  ✅ All {dup_count} copies are IDENTICAL")
                self.log(f"     → Safe to delete duplicates")
                identical_count += 1
            else:
                self.log(f"  ⚠️  Copies have DIFFERENT data!")
                self.log(f"     → Need to decide which to keep")
                different_count += 1

                # Show differences
                for i, row in enumerate(rows[:3], 1):  # Show first 3 copies
                    self.log(f"\n     Copy {i}:")
                    for col_name, value in zip(columns, row):
                        if row != first_row:
                            first_value = first_row[columns.index(col_name)]
                            if value != first_value:
                                self.log(f"       {col_name}: {value} (differs from copy 1: {first_value})")

        # Summary
        self.log(f"\n{'='*70}")
        self.log(f"SUMMARY for {table_name}")
        self.log(f"{'='*70}")
        self.log(f"Examined {len(duplicate_ids)} duplicate IDs:")
        self.log(f"  - {identical_count} have identical copies (safe to delete)")
        self.log(f"  - {different_count} have different data (need review)")

        if different_count > 0:
            self.log(f"\n⚠️  WARNING: Some duplicates have different data!")
            self.log(f"   You need to decide how to handle these.")
            self.log(f"   Options:")
            self.log(f"     1. Keep first inserted (oldest)")
            self.log(f"     2. Keep last inserted (newest)")
            self.log(f"     3. Manually review and merge")

        return {
            'has_duplicates': True,
            'identical_count': identical_count,
            'different_count': different_count,
            'recommendation': 'delete_all' if different_count == 0 else 'needs_review'
        }

    def quick_check(self, table_name, pk_column):
        """
        Quick check: are duplicate rows identical or different?

        Args:
            table_name: Table to check
            pk_column: Primary key column
        """
        self.log(f"\nQuick checking {table_name}...")

        # Get columns (excluding pk_column for comparison)
        self.cursor.execute(f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = '{table_name}'
              AND column_name != '{pk_column}'
            ORDER BY ordinal_position
        """)
        other_columns = [row[0] for row in self.cursor.fetchall()]

        if not other_columns:
            self.log(f"  ℹ️  Table only has PK column, duplicates must be identical")
            return

        # Check if all duplicate groups have identical rows
        # This is a heuristic: we hash all non-PK columns and check if duplicates have same hash
        column_concat = ' || '.join([f"COALESCE({col}::text, '')" for col in other_columns[:10]])  # Limit to 10 cols for speed

        self.cursor.execute(f"""
            WITH row_hashes AS (
                SELECT
                    {pk_column},
                    MD5({column_concat}) as row_hash,
                    COUNT(*) OVER (PARTITION BY {pk_column}) as dup_count
                FROM {table_name}
            ),
            duplicate_groups AS (
                SELECT
                    {pk_column},
                    COUNT(DISTINCT row_hash) as distinct_hashes
                FROM row_hashes
                WHERE dup_count > 1
                GROUP BY {pk_column}
            )
            SELECT
                COUNT(*) as total_dup_groups,
                COUNT(*) FILTER (WHERE distinct_hashes = 1) as identical_groups,
                COUNT(*) FILTER (WHERE distinct_hashes > 1) as different_groups
            FROM duplicate_groups
        """)

        result = self.cursor.fetchone()
        if result[0] == 0:
            self.log(f"  ✅ No duplicates")
        else:
            total, identical, different = result
            self.log(f"  📊 Total duplicate groups: {total:,}")
            self.log(f"     - Identical rows: {identical:,} ({identical/total*100:.1f}%)")
            self.log(f"     - Different data: {different:,} ({different/total*100:.1f}%)")

            if different == 0:
                self.log(f"  ✅ All duplicates are identical - safe to delete")
            else:
                self.log(f"  ⚠️  Some duplicates have different data")

    def check_all_tables(self):
        """Quick check all major tables"""
        self.log("\n" + "="*70)
        self.log("QUICK DUPLICATE CHECK - ALL TABLES")
        self.log("="*70)

        tables = [
            ('works', 'work_id'),
            ('authors', 'author_id'),
            ('authorship', 'work_id'),  # Check by work_id as a proxy
        ]

        for table_name, pk_column in tables:
            try:
                self.quick_check(table_name, pk_column)
            except Exception as e:
                self.log(f"  ❌ Error: {e}")

    def close(self):
        """Close database connection"""
        self.cursor.close()
        self.conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Investigate duplicate records')
    parser.add_argument('--test', action='store_true', help='Use test database')
    parser.add_argument('--table', type=str, help='Specific table to investigate in detail')
    parser.add_argument('--pk', type=str, help='Primary key column (required with --table)')
    parser.add_argument('--quick', action='store_true', help='Run quick check on all tables')
    args = parser.parse_args()

    investigator = DuplicateInvestigator(test_mode=args.test)

    try:
        if args.quick:
            investigator.check_all_tables()
        elif args.table and args.pk:
            investigator.investigate_table(args.table, args.pk)
        else:
            print("Usage:")
            print("  --quick                    Quick check all tables")
            print("  --table <name> --pk <col>  Detailed investigation of specific table")
            sys.exit(1)

    except Exception as e:
        investigator.log(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        investigator.close()

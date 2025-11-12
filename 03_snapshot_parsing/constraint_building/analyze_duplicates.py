#!/usr/bin/env python3
"""
Analyze duplicate records in database tables.
Identifies which tables have duplicates and provides detailed statistics.
"""
import sys
from pathlib import Path
from datetime import datetime
import psycopg2
import argparse
import csv

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
        db_config['database'] = 'OADB_test' if test_mode else 'OADB'

        self.conn = psycopg2.connect(**db_config)
        self.conn.autocommit = False
        self.cursor = self.conn.cursor()

        # Set up file logging
        log_dir = Path('logs')
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

    def analyze_table_duplicates(self, table_name, pk_columns, sample_size=10):
        """
        Analyze duplicates in a table

        Args:
            table_name: Table to analyze
            pk_columns: Primary key columns (string or list)
            sample_size: Number of example duplicates to show

        Returns:
            dict: Analysis results
        """
        if isinstance(pk_columns, str):
            pk_columns = [pk_columns]

        column_list = ', '.join(pk_columns)

        self.log(f"\nAnalyzing {table_name} ({column_list})...")

        # Count total rows
        self.cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_rows = self.cursor.fetchone()[0]

        # Find duplicates
        self.cursor.execute(f"""
            SELECT {column_list}, COUNT(*) as dup_count
            FROM {table_name}
            GROUP BY {column_list}
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC
            LIMIT {sample_size}
        """)

        duplicate_samples = self.cursor.fetchall()

        # Count total duplicate groups
        self.cursor.execute(f"""
            SELECT COUNT(*)
            FROM (
                SELECT {column_list}
                FROM {table_name}
                GROUP BY {column_list}
                HAVING COUNT(*) > 1
            ) dups
        """)

        duplicate_group_count = self.cursor.fetchone()[0]

        # Count total duplicate rows
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
        duplicate_row_count = result if result else 0

        return {
            'table': table_name,
            'pk_columns': pk_columns,
            'total_rows': total_rows,
            'duplicate_groups': duplicate_group_count,
            'duplicate_rows': duplicate_row_count,
            'duplicate_samples': duplicate_samples
        }

    def analyze_all_tables(self):
        """Analyze all tables for duplicates"""
        self.log("\n" + "="*70)
        self.log("DUPLICATE ANALYSIS FOR ALL TABLES")
        self.log("="*70)

        # Define tables and their primary keys
        tables_to_check = [
            # Single-column PKs
            ('works', 'work_id'),
            ('authors', 'author_id'),
            ('institutions', 'institution_id'),
            ('sources', 'source_id'),
            ('publishers', 'publisher_id'),
            ('funders', 'funder_id'),
            ('concepts', 'concept_id'),
            ('topics', 'topic_id'),

            # Composite PKs
            ('authorship', ['work_id', 'author_id', 'author_position']),
            ('work_topics', ['work_id', 'topic_id']),
            ('work_concepts', ['work_id', 'concept_id']),
            ('work_sources', ['work_id', 'source_id']),
            ('citations_by_year', ['work_id', 'year']),
            ('referenced_works', ['work_id', 'referenced_work_id']),
            ('related_works', ['work_id', 'related_work_id']),
        ]

        results = []

        for table_info in tables_to_check:
            if isinstance(table_info, tuple):
                table_name, pk_columns = table_info
            else:
                table_name = table_info
                pk_columns = f"{table_name}_id"

            try:
                result = self.analyze_table_duplicates(table_name, pk_columns)
                results.append(result)

                if result['duplicate_groups'] > 0:
                    self.log(f"  ⚠️  Total rows: {result['total_rows']:,}")
                    self.log(f"  ⚠️  Duplicate groups: {result['duplicate_groups']:,}")
                    self.log(f"  ⚠️  Duplicate rows to remove: {result['duplicate_rows']:,}")
                    self.log(f"  📊 Percentage affected: {result['duplicate_rows']/result['total_rows']*100:.2f}%")

                    self.log(f"\n  Top duplicate examples:")
                    for sample in result['duplicate_samples']:
                        if isinstance(pk_columns, list) and len(pk_columns) > 1:
                            pk_values = ', '.join(str(s) for s in sample[:-1])
                            count = sample[-1]
                        else:
                            pk_values = sample[0]
                            count = sample[1]
                        self.log(f"    {pk_values}: {count} copies")
                else:
                    self.log(f"  ✅ No duplicates found")

            except Exception as e:
                self.log(f"  ❌ Error analyzing {table_name}: {e}")

        # Summary report
        self.log("\n" + "="*70)
        self.log("SUMMARY REPORT")
        self.log("="*70)

        tables_with_duplicates = [r for r in results if r['duplicate_groups'] > 0]

        if tables_with_duplicates:
            self.log(f"\n⚠️  Found duplicates in {len(tables_with_duplicates)} tables:\n")

            self.log(f"{'Table':<25} {'Total Rows':<15} {'Dup Groups':<15} {'Rows to Remove':<15}")
            self.log("-"*70)

            for r in tables_with_duplicates:
                pk_str = ', '.join(r['pk_columns']) if isinstance(r['pk_columns'], list) else r['pk_columns']
                self.log(f"{r['table']:<25} {r['total_rows']:>14,} {r['duplicate_groups']:>14,} {r['duplicate_rows']:>14,}")

            total_dup_rows = sum(r['duplicate_rows'] for r in tables_with_duplicates)
            self.log(f"\n📊 Total duplicate rows to remove: {total_dup_rows:,}")

        else:
            self.log("\n✅ No duplicates found in any table")

        # Save detailed report
        report_file = Path('logs/duplicate_analysis.csv')
        report_file.parent.mkdir(exist_ok=True)

        with open(report_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Table', 'PK Columns', 'Total Rows', 'Duplicate Groups', 'Duplicate Rows', 'Percentage'])

            for r in results:
                pk_str = ', '.join(r['pk_columns']) if isinstance(r['pk_columns'], list) else r['pk_columns']
                pct = r['duplicate_rows']/r['total_rows']*100 if r['total_rows'] > 0 else 0
                writer.writerow([
                    r['table'],
                    pk_str,
                    r['total_rows'],
                    r['duplicate_groups'],
                    r['duplicate_rows'],
                    f"{pct:.2f}%"
                ])

        self.log(f"\n📄 Detailed report saved to: {report_file}")

        return results

    def close(self):
        """Close database connection"""
        self.cursor.close()
        self.conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze duplicate records in database')
    parser.add_argument('--test', action='store_true', help='Use test database')
    args = parser.parse_args()

    analyzer = DuplicateAnalyzer(test_mode=args.test)

    try:
        analyzer.analyze_all_tables()
    except Exception as e:
        analyzer.log(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        analyzer.close()

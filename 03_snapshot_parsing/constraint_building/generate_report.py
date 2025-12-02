#!/usr/bin/env python3
"""
Generate Constraint Building Report for OpenAlex Database
Documents all constraints, indexes, and orphan statistics
"""
import sys
import csv
from pathlib import Path
from datetime import datetime
import psycopg2
import argparse

SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PARENT_DIR))

from config import DB_CONFIG

REPORT_DIR = SCRIPT_DIR / 'reports'
REPORT_DIR.mkdir(parents=True, exist_ok=True)


class ReportGenerator:
    """Generates comprehensive constraint building reports"""

    def __init__(self, test_mode=False):
        """
        Initialize report generator

        Args:
            test_mode: Use test database (oadb2_test)
        """
        self.test_mode = test_mode
        db_config = DB_CONFIG.copy()
        db_config['database'] = 'oadbv5_test' if test_mode else 'oadbv5'

        self.conn = psycopg2.connect(**db_config)
        self.cursor = self.conn.cursor()

        # Set up file logging
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        self.log_file = log_dir / 'generate_report.log'

        self.log(f"Connected to database: {db_config['database']}")
        self.log(f"Log file: {self.log_file}")
        self.db_name = db_config['database']

    def log(self, message):
        """Print timestamped message to console and file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] {message}"
        print(log_line)

        # Also write to file
        with open(self.log_file, 'a') as f:
            f.write(log_line + '\n')

    def get_primary_keys(self):
        """Get all primary key constraints"""
        query = """
            SELECT
                tc.table_name,
                tc.constraint_name,
                string_agg(kcu.column_name, ', ' ORDER BY kcu.ordinal_position) as columns
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            WHERE tc.constraint_type = 'PRIMARY KEY'
              AND tc.table_schema = 'public'
            GROUP BY tc.table_name, tc.constraint_name
            ORDER BY tc.table_name
        """

        self.cursor.execute(query)
        return self.cursor.fetchall()

    def get_foreign_keys(self):
        """Get all foreign key constraints"""
        query = """
            SELECT
                tc.table_name,
                tc.constraint_name,
                kcu.column_name,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name,
                pgc.convalidated as is_valid
            FROM information_schema.table_constraints AS tc
            JOIN information_schema.key_column_usage AS kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            JOIN pg_constraint pgc ON tc.constraint_name = pgc.conname
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND tc.table_schema = 'public'
            ORDER BY tc.table_name, tc.constraint_name
        """

        self.cursor.execute(query)
        return self.cursor.fetchall()

    def get_indexes(self):
        """Get all indexes"""
        query = """
            SELECT
                tablename,
                indexname,
                indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
              AND indexname NOT LIKE '%_pkey'
            ORDER BY tablename, indexname
        """

        self.cursor.execute(query)
        return self.cursor.fetchall()

    def get_table_row_counts(self):
        """Get row counts for all tables"""
        query = """
            SELECT
                schemaname,
                relname,
                n_live_tup
            FROM pg_stat_user_tables
            WHERE schemaname = 'public'
            ORDER BY n_live_tup DESC
        """

        self.cursor.execute(query)
        return self.cursor.fetchall()

    def generate_all_reports(self):
        """Generate all constraint building reports"""
        self.log("\n" + "="*70)
        self.log("GENERATING CONSTRAINT BUILDING REPORTS")
        self.log(f"Database: {self.db_name}")
        self.log("="*70 + "\n")

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Report 1: Primary Keys
        self.log("Generating primary keys report...")
        pks = self.get_primary_keys()
        pk_report = REPORT_DIR / f'primary_keys_{timestamp}.csv'

        with open(pk_report, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['table_name', 'constraint_name', 'columns'])
            for row in pks:
                writer.writerow(row)

        self.log(f"  ✅ Primary keys report: {pk_report.name} ({len(pks)} PKs)")

        # Report 2: Foreign Keys
        self.log("Generating foreign keys report...")
        fks = self.get_foreign_keys()
        fk_report = REPORT_DIR / f'foreign_keys_{timestamp}.csv'

        with open(fk_report, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['table_name', 'constraint_name', 'column', 'references_table', 'references_column', 'is_valid'])
            for row in fks:
                writer.writerow(row)

        valid_fks = sum(1 for row in fks if row[5])
        invalid_fks = sum(1 for row in fks if not row[5])

        self.log(f"  ✅ Foreign keys report: {fk_report.name}")
        self.log(f"     Total FKs: {len(fks)}")
        self.log(f"     Valid: {valid_fks}")
        self.log(f"     Invalid (NOT VALID): {invalid_fks}")

        # Report 3: Indexes
        self.log("Generating indexes report...")
        indexes = self.get_indexes()
        index_report = REPORT_DIR / f'indexes_{timestamp}.csv'

        with open(index_report, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['table_name', 'index_name', 'definition'])
            for row in indexes:
                writer.writerow(row)

        self.log(f"  ✅ Indexes report: {index_report.name} ({len(indexes)} indexes)")

        # Report 4: Table Statistics
        self.log("Generating table statistics report...")
        table_stats = self.get_table_row_counts()
        stats_report = REPORT_DIR / f'table_statistics_{timestamp}.csv'

        with open(stats_report, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['schema', 'table_name', 'row_count'])
            for row in table_stats:
                writer.writerow(row)

        self.log(f"  ✅ Table statistics report: {stats_report.name}")

        # Report 5: Summary Report
        self.log("Generating summary report...")
        summary_report = REPORT_DIR / f'CONSTRAINT_SUMMARY_{timestamp}.md'

        with open(summary_report, 'w') as f:
            f.write(f"# OpenAlex Database Constraint Building Summary\n\n")
            f.write(f"**Database:** {self.db_name}\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("---\n\n")
            f.write("## Primary Keys\n\n")
            f.write(f"Total primary keys created: **{len(pks)}**\n\n")

            f.write("| Table | Constraint Name | Columns |\n")
            f.write("|-------|-----------------|----------|\n")
            for table, constraint, columns in pks:
                f.write(f"| {table} | {constraint} | {columns} |\n")

            f.write("\n---\n\n")
            f.write("## Foreign Keys\n\n")
            f.write(f"Total foreign keys: **{len(fks)}**\n")
            f.write(f"- Valid: **{valid_fks}**\n")
            f.write(f"- Invalid (NOT VALID): **{invalid_fks}**\n\n")

            if invalid_fks > 0:
                f.write("⚠️ **Invalid foreign keys have orphaned records that need API retrieval**\n\n")

            f.write("| Table | Constraint | Column | References | Valid |\n")
            f.write("|-------|------------|--------|------------|-------|\n")
            for table, constraint, col, ref_table, ref_col, valid in fks:
                valid_icon = '✅' if valid else '❌'
                f.write(f"| {table} | {constraint} | {col} | {ref_table}.{ref_col} | {valid_icon} |\n")

            f.write("\n---\n\n")
            f.write("## Indexes\n\n")
            f.write(f"Total indexes created: **{len(indexes)}**\n\n")

            f.write("---\n\n")
            f.write("## Table Statistics\n\n")
            f.write("| Table | Row Count |\n")
            f.write("|-------|----------:|\n")
            for schema, table, count in table_stats[:20]:  # Top 20 tables
                f.write(f"| {table} | {count:,} |\n")

            f.write("\n---\n\n")
            f.write("## Next Steps\n\n")

            if invalid_fks > 0:
                f.write("1. Review orphan manifests in `orphan_manifests/` directory\n")
                f.write("2. Retrieve missing entities via OpenAlex API using orphan manifests\n")
                f.write("3. Re-run validation after retrieving missing entities\n\n")
            else:
                f.write("✅ All constraints validated successfully!\n\n")

            f.write("## Files Generated\n\n")
            f.write(f"- `{pk_report.name}` - Primary keys detail\n")
            f.write(f"- `{fk_report.name}` - Foreign keys detail\n")
            f.write(f"- `{index_report.name}` - Indexes detail\n")
            f.write(f"- `{stats_report.name}` - Table statistics\n")

        self.log(f"  ✅ Summary report: {summary_report.name}")

        self.log("\n" + "="*70)
        self.log(f"REPORT GENERATION COMPLETE")
        self.log(f"Reports saved to: {REPORT_DIR}")
        self.log("="*70 + "\n")

    def close(self):
        """Close database connection"""
        self.cursor.close()
        self.conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate Constraint Building Reports')
    parser.add_argument('--test', action='store_true', help='Use test database (oadb2_test)')
    args = parser.parse_args()

    generator = ReportGenerator(test_mode=args.test)

    try:
        generator.generate_all_reports()
    except Exception as e:
        generator.log(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        generator.close()

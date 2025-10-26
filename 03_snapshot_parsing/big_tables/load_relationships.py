#!/usr/bin/env python3
"""
Load Relationships from CSV into PostgreSQL
Handles: COPY → Validate → Clean → Add FKs → Index
"""
import psycopg2
import argparse
import sys
from pathlib import Path
from datetime import datetime
import json

from config import DB_CONFIG

# CSV source directory
CSV_SOURCE_DIR = Path('/Volumes/OA_snapshot/works_tables')

# FK violation threshold (default 1%)
FK_VIOLATION_THRESHOLD = 0.01

class RelationshipLoader:
    """Load relationship data from CSV into database tables"""

    # Table definitions with columns and FK constraints
    TABLE_DEFINITIONS = {
        'authorship': {
            'columns': ['work_id', 'author_id', 'author_position', 'is_corresponding',
                       'raw_affiliation_string', 'institution_id'],
            'pk': '(work_id, author_id)',
            'fks': [
                ('work_id', 'works', 'work_id'),
                ('author_id', 'authors', 'author_id')
            ],
            'indexes': ['work_id', 'author_id']
        },
        'work_topics': {
            'columns': ['work_id', 'topic_id', 'score', 'is_primary_topic'],
            'pk': '(work_id, topic_id)',
            'fks': [
                ('work_id', 'works', 'work_id'),
                ('topic_id', 'topics', 'topic_id')
            ],
            'indexes': ['work_id', 'topic_id']
        },
        'work_concepts': {
            'columns': ['work_id', 'concept_id', 'score'],
            'pk': '(work_id, concept_id)',
            'fks': [
                ('work_id', 'works', 'work_id'),
                ('concept_id', 'concepts', 'concept_id')
            ],
            'indexes': ['work_id', 'concept_id']
        },
        'work_sources': {
            'columns': ['work_id', 'source_id'],
            'pk': '(work_id, source_id)',
            'fks': [
                ('work_id', 'works', 'work_id'),
                ('source_id', 'sources', 'source_id')
            ],
            'indexes': ['work_id', 'source_id']
        },
        'citations_by_year': {
            'columns': ['work_id', 'year', 'citation_count'],
            'pk': '(work_id, year)',
            'fks': [
                ('work_id', 'works', 'work_id')
            ],
            'indexes': ['work_id', 'year']
        },
        'referenced_works': {
            'columns': ['work_id', 'referenced_work_id'],
            'pk': '(work_id, referenced_work_id)',
            'fks': [
                ('work_id', 'works', 'work_id')
                # Note: referenced_work_id may not exist in works table (external references)
            ],
            'indexes': ['work_id', 'referenced_work_id']
        },
        'related_works': {
            'columns': ['work_id', 'related_work_id'],
            'pk': '(work_id, related_work_id)',
            'fks': [
                ('work_id', 'works', 'work_id')
            ],
            'indexes': ['work_id', 'related_work_id']
        },
        'alternate_ids': {
            'columns': ['work_id', 'id_type', 'id_value'],
            'pk': None,  # Serial primary key
            'fks': [
                ('work_id', 'works', 'work_id')
            ],
            'indexes': ['work_id', 'id_type']
        },
        'work_keywords': {
            'columns': ['work_id', 'keyword'],
            'pk': '(work_id, keyword)',
            'fks': [
                ('work_id', 'works', 'work_id')
            ],
            'indexes': ['work_id']
        },
        'work_funders': {
            'columns': ['work_id', 'funder_id', 'award_id'],
            'pk': '(work_id, funder_id)',
            'fks': [
                ('work_id', 'works', 'work_id'),
                ('funder_id', 'funders', 'funder_id')
            ],
            'indexes': ['work_id', 'funder_id']
        },
        'apc': {
            'columns': ['work_id', 'value', 'currency', 'value_usd', 'provenance'],
            'pk': 'work_id',
            'fks': [
                ('work_id', 'works', 'work_id')
            ],
            'indexes': []
        }
    }

    def __init__(self, table_name: str, csv_dir: Path = CSV_SOURCE_DIR,
                 fk_threshold: float = FK_VIOLATION_THRESHOLD):
        self.table_name = table_name
        self.csv_dir = csv_dir
        self.fk_threshold = fk_threshold

        if table_name not in self.TABLE_DEFINITIONS:
            raise ValueError(f"Unknown table: {table_name}")

        self.table_def = self.TABLE_DEFINITIONS[table_name]
        self.conn = None
        self.stats = {}

    def log(self, message: str):
        """Print with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {message}")

    def create_table(self):
        """Create table without FK constraints"""
        self.log(f"Creating table: {self.table_name}")

        # Drop existing table
        cursor = self.conn.cursor()
        cursor.execute(f"DROP TABLE IF EXISTS {self.table_name} CASCADE;")
        self.conn.commit()

        # Build CREATE TABLE statement
        columns = self.table_def['columns']
        pk = self.table_def['pk']

        # Map column types
        col_types = []
        for col in columns:
            if col.endswith('_id'):
                col_types.append(f"{col} VARCHAR(255)")
            elif col in ['score', 'value', 'value_usd']:
                col_types.append(f"{col} DECIMAL(15,2)")
            elif col in ['is_corresponding', 'is_primary_topic']:
                col_types.append(f"{col} BOOLEAN")
            elif col in ['year', 'citation_count']:
                col_types.append(f"{col} INTEGER")
            elif col == 'keyword':
                col_types.append(f"{col} VARCHAR(255)")
            else:
                col_types.append(f"{col} TEXT")

        create_sql = f"CREATE TABLE {self.table_name} (\n"
        if self.table_name == 'alternate_ids':
            create_sql += "  alt_id SERIAL PRIMARY KEY,\n"
        create_sql += "  " + ",\n  ".join(col_types)

        if pk and self.table_name != 'alternate_ids':
            create_sql += f",\n  PRIMARY KEY {pk}"

        create_sql += "\n);"

        cursor.execute(create_sql)
        self.conn.commit()
        cursor.close()

        self.log(f"  ✅ Table created (no FK constraints yet)")

    def find_csv_files(self):
        """Find all CSV files for this table"""
        pattern = f"{self.table_name}_*.csv"
        csv_files = sorted(self.csv_dir.glob(pattern))

        if not csv_files:
            raise FileNotFoundError(f"No CSV files found for {self.table_name} in {self.csv_dir}")

        self.log(f"Found {len(csv_files)} CSV files to load")
        return csv_files

    def load_csv_files(self, csv_files):
        """Bulk load CSV files using COPY"""
        self.log("Loading CSV files...")

        cursor = self.conn.cursor()

        # Disable triggers and constraints during load
        cursor.execute("SET session_replication_role = replica;")

        total_loaded = 0

        for i, csv_file in enumerate(csv_files, 1):
            self.log(f"  [{i}/{len(csv_files)}] Loading {csv_file.name}...")

            with open(csv_file, 'r') as f:
                cursor.copy_expert(
                    f"COPY {self.table_name} ({','.join(self.table_def['columns'])}) "
                    f"FROM STDIN WITH CSV",
                    f
                )

            loaded = cursor.rowcount
            total_loaded += loaded
            self.log(f"      ✅ Loaded {loaded:,} records")

        # Re-enable triggers
        cursor.execute("SET session_replication_role = default;")
        self.conn.commit()
        cursor.close()

        self.stats['total_loaded'] = total_loaded
        self.log(f"\n  Total records loaded: {total_loaded:,}")

    def analyze_fk_violations(self):
        """Analyze FK violations before adding constraints"""
        self.log("\nAnalyzing FK violations...")

        cursor = self.conn.cursor()
        violations = {}

        for fk_col, ref_table, ref_col in self.table_def['fks']:
            self.log(f"  Checking {fk_col} → {ref_table}({ref_col})...")

            # Find orphaned records
            cursor.execute(f"""
                SELECT COUNT(*)
                FROM {self.table_name} t
                WHERE t.{fk_col} IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM {ref_table} r
                      WHERE r.{ref_col} = t.{fk_col}
                  );
            """)

            orphaned_count = cursor.fetchone()[0]
            total_count = self.stats['total_loaded']
            violation_rate = orphaned_count / total_count if total_count > 0 else 0

            violations[fk_col] = {
                'count': orphaned_count,
                'rate': violation_rate,
                'ref_table': ref_table
            }

            self.log(f"      Orphaned {fk_col}: {orphaned_count:,} ({100*violation_rate:.2f}%)")

            # Sample orphaned values
            if orphaned_count > 0:
                cursor.execute(f"""
                    SELECT DISTINCT t.{fk_col}
                    FROM {self.table_name} t
                    WHERE t.{fk_col} IS NOT NULL
                      AND NOT EXISTS (
                          SELECT 1 FROM {ref_table} r
                          WHERE r.{ref_col} = t.{fk_col}
                      )
                    LIMIT 5;
                """)
                samples = [row[0] for row in cursor.fetchall()]
                self.log(f"      Sample orphaned values: {samples}")

        cursor.close()
        self.stats['fk_violations'] = violations

        # Check if violations exceed threshold
        total_violations = sum(v['count'] for v in violations.values())
        total_violation_rate = total_violations / self.stats['total_loaded'] if self.stats['total_loaded'] > 0 else 0

        self.log(f"\n  Total FK violations: {total_violations:,} ({100*total_violation_rate:.2f}%)")

        if total_violation_rate > self.fk_threshold:
            self.log(f"  ❌ FAIL: Violation rate ({100*total_violation_rate:.2f}%) exceeds threshold ({100*self.fk_threshold:.2f}%)")
            return False
        else:
            self.log(f"  ✅ PASS: Violation rate within acceptable threshold")
            return True

    def clean_orphaned_records(self):
        """Delete orphaned records that violate FK constraints"""
        self.log("\nCleaning orphaned records...")

        cursor = self.conn.cursor()
        total_deleted = 0

        for fk_col, ref_table, ref_col in self.table_def['fks']:
            self.log(f"  Cleaning {fk_col} → {ref_table}({ref_col})...")

            # Delete orphaned records
            cursor.execute(f"""
                DELETE FROM {self.table_name} t
                WHERE t.{fk_col} IS NOT NULL
                  AND NOT EXISTS (
                      SELECT 1 FROM {ref_table} r
                      WHERE r.{ref_col} = t.{fk_col}
                  );
            """)

            deleted_count = cursor.rowcount
            total_deleted += deleted_count
            self.log(f"      ✅ Deleted {deleted_count:,} orphaned records")

        self.conn.commit()
        cursor.close()

        self.stats['total_deleted'] = total_deleted
        self.log(f"\n  Total records deleted: {total_deleted:,}")

        # Final count
        cursor = self.conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {self.table_name};")
        final_count = cursor.fetchone()[0]
        cursor.close()

        self.stats['final_count'] = final_count
        self.log(f"  Final record count: {final_count:,}")

    def add_foreign_keys(self):
        """Add FK constraints to table"""
        self.log("\nAdding foreign key constraints...")

        cursor = self.conn.cursor()

        for i, (fk_col, ref_table, ref_col) in enumerate(self.table_def['fks'], 1):
            constraint_name = f"fk_{self.table_name}_{fk_col}"

            self.log(f"  [{i}/{len(self.table_def['fks'])}] Adding {constraint_name}...")

            cursor.execute(f"""
                ALTER TABLE {self.table_name}
                ADD CONSTRAINT {constraint_name}
                FOREIGN KEY ({fk_col})
                REFERENCES {ref_table}({ref_col})
                ON DELETE CASCADE;
            """)

            self.log(f"      ✅ Added")

        self.conn.commit()
        cursor.close()

    def create_indexes(self):
        """Create indexes on table"""
        self.log("\nCreating indexes...")

        cursor = self.conn.cursor()
        index_cols = self.table_def['indexes']

        for i, col in enumerate(index_cols, 1):
            index_name = f"idx_{self.table_name}_{col}"

            self.log(f"  [{i}/{len(index_cols)}] Creating {index_name}...")

            cursor.execute(f"""
                CREATE INDEX IF NOT EXISTS {index_name}
                ON {self.table_name}({col});
            """)

            self.log(f"      ✅ Created")

        self.conn.commit()
        cursor.close()

    def generate_report(self):
        """Generate final report"""
        self.log("\n" + "=" * 80)
        self.log(f"LOADING REPORT: {self.table_name}")
        self.log("=" * 80)
        self.log(f"Records loaded: {self.stats.get('total_loaded', 0):,}")
        self.log(f"Records deleted (FK violations): {self.stats.get('total_deleted', 0):,}")
        self.log(f"Final record count: {self.stats.get('final_count', 0):,}")

        self.log("\nFK Violation Details:")
        for fk_col, violation_info in self.stats.get('fk_violations', {}).items():
            self.log(f"  {fk_col} → {violation_info['ref_table']}: "
                    f"{violation_info['count']:,} violations ({100*violation_info['rate']:.2f}%)")

        self.log("=" * 80)

        # Save report to JSON
        report_file = Path(f"{self.table_name}_load_report.json")
        with open(report_file, 'w') as f:
            json.dump(self.stats, f, indent=2, default=str)
        self.log(f"\nReport saved to: {report_file}")

    def load(self):
        """Main loading process"""
        try:
            # Connect to database
            self.log(f"Connecting to database...")
            self.conn = psycopg2.connect(**DB_CONFIG)
            self.conn.autocommit = False

            # Find CSV files
            csv_files = self.find_csv_files()

            # Create table
            self.create_table()

            # Load CSV files
            self.load_csv_files(csv_files)

            # Analyze FK violations
            violations_ok = self.analyze_fk_violations()

            if not violations_ok:
                self.log("\n⚠️  WARNING: FK violation rate exceeds threshold")
                self.log("Options:")
                self.log("  1. Proceed with cleaning (will delete orphaned records)")
                self.log("  2. Abort and investigate")

                response = input("\nProceed with cleaning? (yes/no): ")
                if response.lower() != 'yes':
                    self.log("❌ Aborted by user")
                    return False

            # Clean orphaned records
            self.clean_orphaned_records()

            # Add FK constraints
            self.add_foreign_keys()

            # Create indexes
            self.create_indexes()

            # Generate report
            self.generate_report()

            self.log("\n✅ LOADING COMPLETE")
            return True

        except KeyboardInterrupt:
            self.log("\n⚠️  Interrupted by user")
            if self.conn:
                self.conn.rollback()
            return False

        except Exception as e:
            self.log(f"\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            if self.conn:
                self.conn.rollback()
            return False

        finally:
            if self.conn:
                self.conn.close()

def main():
    parser = argparse.ArgumentParser(
        description="Load relationship data from CSV into PostgreSQL",
        epilog="""
Examples:
  # Load authorship table
  python3 load_relationships.py --table authorship

  # Load with custom CSV directory
  python3 load_relationships.py --table work_topics --csv-dir /path/to/csvs

  # Set stricter FK violation threshold (0.5%)
  python3 load_relationships.py --table work_concepts --threshold 0.005
        """
    )

    parser.add_argument('--table', required=True,
                       choices=list(RelationshipLoader.TABLE_DEFINITIONS.keys()),
                       help="Table to load")
    parser.add_argument('--csv-dir', default=str(CSV_SOURCE_DIR),
                       help=f"CSV source directory (default: {CSV_SOURCE_DIR})")
    parser.add_argument('--threshold', type=float, default=FK_VIOLATION_THRESHOLD,
                       help=f"FK violation threshold (default: {FK_VIOLATION_THRESHOLD})")

    args = parser.parse_args()

    loader = RelationshipLoader(
        args.table,
        csv_dir=Path(args.csv_dir),
        fk_threshold=args.threshold
    )

    success = loader.load()
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()

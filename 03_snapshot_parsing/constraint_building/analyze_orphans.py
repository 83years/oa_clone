#!/usr/bin/env python3
"""
Orphan Record Analysis for OpenAlex Database
Identifies records with foreign keys pointing to non-existent entities
Generates manifests for API retrieval
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

ORPHAN_MANIFEST_DIR = SCRIPT_DIR / 'orphan_manifests'
ORPHAN_MANIFEST_DIR.mkdir(parents=True, exist_ok=True)


class OrphanAnalyzer:
    """Analyzes orphaned foreign key references"""

    def __init__(self, test_mode=False):
        """
        Initialize orphan analyzer

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
        self.log_file = log_dir / 'analyze_orphans.log'

        self.log(f"Connected to database: {db_config['database']}")
        self.log(f"Log file: {self.log_file}")

        self.orphan_stats = {}

    def log(self, message):
        """Print timestamped message to console and file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] {message}"
        print(log_line)

        # Also write to file
        with open(self.log_file, 'a') as f:
            f.write(log_line + '\n')

    def find_orphans(self, child_table, child_column, parent_table, parent_column, entity_type):
        """
        Find orphaned records where child FK doesn't exist in parent table

        Args:
            child_table: Table with foreign key
            child_column: Column containing foreign key
            parent_table: Referenced parent table
            parent_column: Referenced parent column
            entity_type: Entity type name for manifest file

        Returns:
            tuple: (orphan_count, orphan_ids_sample)
        """
        self.log(f"  Analyzing {child_table}.{child_column} → {parent_table}.{parent_column}...")

        # Find orphaned IDs
        query = f"""
            SELECT DISTINCT c.{child_column}
            FROM {child_table} c
            LEFT JOIN {parent_table} p ON c.{child_column} = p.{parent_column}
            WHERE c.{child_column} IS NOT NULL
              AND p.{parent_column} IS NULL
        """

        self.cursor.execute(query)
        orphan_ids = [row[0] for row in self.cursor.fetchall()]
        orphan_count = len(orphan_ids)

        if orphan_count > 0:
            self.log(f"    ⚠️  Found {orphan_count:,} orphaned {entity_type} IDs")

            # Save orphan IDs to manifest file
            manifest_file = ORPHAN_MANIFEST_DIR / f"{child_table}_{child_column}_orphans.csv"
            with open(manifest_file, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['orphaned_id', 'entity_type', 'child_table', 'child_column'])
                for orphan_id in orphan_ids:
                    writer.writerow([orphan_id, entity_type, child_table, child_column])

            self.log(f"    📝 Manifest saved: {manifest_file.name}")
        else:
            self.log(f"    ✅ No orphans found")

        # Track statistics
        key = f"{child_table}.{child_column} → {parent_table}.{parent_column}"
        self.orphan_stats[key] = {
            'entity_type': entity_type,
            'orphan_count': orphan_count,
            'sample_ids': orphan_ids[:10] if orphan_ids else []
        }

        return orphan_count, orphan_ids[:10]

    def analyze_all_orphans(self):
        """Analyze orphans in all critical foreign key relationships"""
        self.log("\n" + "="*70)
        self.log("ORPHAN ANALYSIS - FOREIGN KEY INTEGRITY CHECK")
        self.log("="*70 + "\n")

        total_orphans = 0

        # Authorship table (CRITICAL)
        self.log("Analyzing AUTHORSHIP table...")
        total_orphans += self.find_orphans('authorship', 'author_id', 'authors', 'author_id', 'author')
        total_orphans += self.find_orphans('authorship', 'work_id', 'works', 'work_id', 'work')
        total_orphans += self.find_orphans('authorship', 'institution_id', 'institutions', 'institution_id', 'institution')

        # Work relationships
        self.log("\nAnalyzing WORK RELATIONSHIP tables...")
        total_orphans += self.find_orphans('work_topics', 'work_id', 'works', 'work_id', 'work')
        total_orphans += self.find_orphans('work_topics', 'topic_id', 'topics', 'topic_id', 'topic')
        total_orphans += self.find_orphans('work_concepts', 'work_id', 'works', 'work_id', 'work')
        total_orphans += self.find_orphans('work_concepts', 'concept_id', 'concepts', 'concept_id', 'concept')
        total_orphans += self.find_orphans('work_sources', 'work_id', 'works', 'work_id', 'work')
        total_orphans += self.find_orphans('work_sources', 'source_id', 'sources', 'source_id', 'source')
        total_orphans += self.find_orphans('work_keywords', 'work_id', 'works', 'work_id', 'work')
        total_orphans += self.find_orphans('work_funders', 'work_id', 'works', 'work_id', 'work')
        total_orphans += self.find_orphans('work_funders', 'funder_id', 'funders', 'funder_id', 'funder')

        # Citations and references
        self.log("\nAnalyzing CITATION tables...")
        total_orphans += self.find_orphans('citations_by_year', 'work_id', 'works', 'work_id', 'work')
        total_orphans += self.find_orphans('referenced_works', 'work_id', 'works', 'work_id', 'work')
        total_orphans += self.find_orphans('referenced_works', 'referenced_work_id', 'works', 'work_id', 'work')
        total_orphans += self.find_orphans('related_works', 'work_id', 'works', 'work_id', 'work')
        total_orphans += self.find_orphans('related_works', 'related_work_id', 'works', 'work_id', 'work')

        # Author relationships
        self.log("\nAnalyzing AUTHOR RELATIONSHIP tables...")
        total_orphans += self.find_orphans('author_topics', 'author_id', 'authors', 'author_id', 'author')
        total_orphans += self.find_orphans('author_topics', 'topic_id', 'topics', 'topic_id', 'topic')
        total_orphans += self.find_orphans('author_concepts', 'author_id', 'authors', 'author_id', 'author')
        total_orphans += self.find_orphans('author_concepts', 'concept_id', 'concepts', 'concept_id', 'concept')
        total_orphans += self.find_orphans('author_institutions', 'author_id', 'authors', 'author_id', 'author')
        total_orphans += self.find_orphans('author_institutions', 'institution_id', 'institutions', 'institution_id', 'institution')
        total_orphans += self.find_orphans('authors_works_by_year', 'author_id', 'authors', 'author_id', 'author')

        # Source relationships
        self.log("\nAnalyzing SOURCE RELATIONSHIP tables...")
        total_orphans += self.find_orphans('source_publishers', 'source_id', 'sources', 'source_id', 'source')
        total_orphans += self.find_orphans('source_publishers', 'publisher_id', 'publishers', 'publisher_id', 'publisher')

        # Institution relationships
        self.log("\nAnalyzing INSTITUTION RELATIONSHIP tables...")
        total_orphans += self.find_orphans('institution_geo', 'institution_id', 'institutions', 'institution_id', 'institution')
        total_orphans += self.find_orphans('institution_hierarchy', 'parent_institution_id', 'institutions', 'institution_id', 'institution')
        total_orphans += self.find_orphans('institution_hierarchy', 'child_institution_id', 'institutions', 'institution_id', 'institution')

        # Topic hierarchy
        self.log("\nAnalyzing TOPIC HIERARCHY table...")
        total_orphans += self.find_orphans('topic_hierarchy', 'parent_topic_id', 'topics', 'topic_id', 'topic')
        total_orphans += self.find_orphans('topic_hierarchy', 'child_topic_id', 'topics', 'topic_id', 'topic')

        # Other tables
        self.log("\nAnalyzing OTHER tables...")
        total_orphans += self.find_orphans('author_name_variants', 'author_id', 'authors', 'author_id', 'author')

        # Generate summary report
        self.generate_summary_report()

        self.log("\n" + "="*70)
        self.log(f"ORPHAN ANALYSIS COMPLETE")
        self.log(f"Total orphaned references found: {total_orphans:,}")
        self.log(f"Manifest files saved to: {ORPHAN_MANIFEST_DIR}")
        self.log("="*70 + "\n")

    def generate_summary_report(self):
        """Generate summary report of all orphans found"""
        report_file = ORPHAN_MANIFEST_DIR / 'orphan_summary_report.csv'

        with open(report_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['relationship', 'entity_type', 'orphan_count', 'sample_ids'])

            for relationship, stats in self.orphan_stats.items():
                sample_ids = ', '.join(stats['sample_ids'][:5])
                writer.writerow([
                    relationship,
                    stats['entity_type'],
                    stats['orphan_count'],
                    sample_ids
                ])

        self.log(f"\n📊 Summary report saved: {report_file.name}")

    def close(self):
        """Close database connection"""
        self.cursor.close()
        self.conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze Orphaned Records')
    parser.add_argument('--test', action='store_true', help='Use test database (oadb2_test)')
    args = parser.parse_args()

    analyzer = OrphanAnalyzer(test_mode=args.test)

    try:
        analyzer.analyze_all_orphans()
    except Exception as e:
        analyzer.log(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        analyzer.close()

#!/usr/bin/env python3
"""
Parse OpenAlex Works - Phase 2: Extract Relationships to CSV
Extracts all joining table relationships from works files and writes to CSV files
"""
import json
import gzip
import argparse
import sys
import csv
from pathlib import Path
from datetime import datetime

from config import DATA_ROOT
from utils import setup_logging, get_file_info, PerformanceMonitor

# CSV output directory
CSV_OUTPUT_DIR = Path('/Volumes/OA_snapshot/works_tables')

PROGRESS_INTERVAL = 5000

class RelationshipExtractor:
    """Extract all relationships from works JSON to CSV files"""

    def __init__(self, input_file: str, output_dir: Path = CSV_OUTPUT_DIR):
        self.input_file = input_file
        self.output_dir = output_dir

        # Setup logging
        self.logger, self.log_file = setup_logging("relationships_extractor")
        self.logger.info(f"Starting relationship extraction for {input_file}")

        # Performance monitoring
        self.monitor = PerformanceMonitor(self.logger, report_interval=PROGRESS_INTERVAL)
        file_info = get_file_info(input_file)
        self.logger.info(f"File size: {file_info['file_size_mb']:.1f} MB")
        if file_info['line_count_estimate']:
            self.logger.info(f"Estimated lines: {file_info['line_count_estimate']:,}")
            self.monitor.set_estimated_total(file_info['line_count_estimate'])

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # CSV writers (will be initialized in setup_csv_writers)
        self.csv_writers = {}
        self.csv_files = {}

        # Stats
        self.stats = {
            'works_processed': 0,
            'authorship': 0,
            'work_topics': 0,
            'work_concepts': 0,
            'work_sources': 0,
            'citations_by_year': 0,
            'referenced_works': 0,
            'related_works': 0,
            'alternate_ids': 0,
            'work_keywords': 0,
            'work_funders': 0,
            'apc': 0,
            'errors': 0
        }

    def setup_csv_writers(self):
        """Setup CSV writers for all relationship tables"""

        # Define CSV schemas
        schemas = {
            'authorship': ['work_id', 'author_id', 'author_position', 'is_corresponding',
                          'raw_affiliation_string', 'institution_id'],
            'work_topics': ['work_id', 'topic_id', 'score', 'is_primary_topic'],
            'work_concepts': ['work_id', 'concept_id', 'score'],
            'work_sources': ['work_id', 'source_id'],
            'citations_by_year': ['work_id', 'year', 'citation_count'],
            'referenced_works': ['work_id', 'referenced_work_id'],
            'related_works': ['work_id', 'related_work_id'],
            'alternate_ids': ['work_id', 'id_type', 'id_value'],
            'work_keywords': ['work_id', 'keyword'],
            'work_funders': ['work_id', 'funder_id', 'award_id'],
            'apc': ['work_id', 'value', 'currency', 'value_usd', 'provenance']
        }

        # Get file basename for unique CSV names
        input_path = Path(self.input_file)
        base_name = input_path.stem  # e.g., "part_000"

        # Create CSV writers
        for table_name, columns in schemas.items():
            csv_path = self.output_dir / f"{table_name}_{base_name}.csv"
            csv_file = open(csv_path, 'w', newline='', encoding='utf-8')
            writer = csv.writer(csv_file, quoting=csv.QUOTE_MINIMAL)

            self.csv_files[table_name] = csv_file
            self.csv_writers[table_name] = writer

            self.logger.info(f"  CSV output: {csv_path}")

    def extract_authorship(self, work_id: str, work: dict):
        """Extract authorship relationships"""
        authorships = work.get('authorships', [])

        for authorship in authorships:
            author = authorship.get('author', {})
            author_id = author.get('id', '').replace('https://openalex.org/', '')

            if not author_id:
                continue

            # Get institutions (take first if multiple)
            institutions = authorship.get('institutions', [])
            institution_id = None
            if institutions:
                inst = institutions[0]
                inst_id = inst.get('id', '').replace('https://openalex.org/', '')
                institution_id = inst_id if inst_id else None

            # Get raw affiliation string
            raw_affs = authorship.get('raw_affiliation_strings', [])
            raw_aff_str = raw_affs[0] if raw_affs else None

            self.csv_writers['authorship'].writerow([
                work_id,
                author_id,
                authorship.get('author_position'),
                authorship.get('is_corresponding', False),
                raw_aff_str,
                institution_id
            ])

            self.stats['authorship'] += 1

    def extract_work_topics(self, work_id: str, work: dict):
        """Extract work-topic relationships"""
        topics = work.get('topics', [])
        primary_topic = work.get('primary_topic', {})
        primary_topic_id = primary_topic.get('id', '').replace('https://openalex.org/', '') if primary_topic else None

        for topic in topics:
            topic_id = topic.get('id', '').replace('https://openalex.org/', '')
            if not topic_id:
                continue

            is_primary = (topic_id == primary_topic_id)

            self.csv_writers['work_topics'].writerow([
                work_id,
                topic_id,
                topic.get('score'),
                is_primary
            ])

            self.stats['work_topics'] += 1

    def extract_work_concepts(self, work_id: str, work: dict):
        """Extract work-concept relationships"""
        concepts = work.get('concepts', [])

        for concept in concepts:
            concept_id = concept.get('id', '').replace('https://openalex.org/', '')
            if not concept_id:
                continue

            self.csv_writers['work_concepts'].writerow([
                work_id,
                concept_id,
                concept.get('score')
            ])

            self.stats['work_concepts'] += 1

    def extract_work_sources(self, work_id: str, work: dict):
        """Extract work-source relationships"""
        # Primary location source
        primary_location = work.get('primary_location', {})
        if primary_location:
            source = primary_location.get('source', {})
            if source:
                source_id = source.get('id', '').replace('https://openalex.org/', '')
                if source_id:
                    self.csv_writers['work_sources'].writerow([work_id, source_id])
                    self.stats['work_sources'] += 1

        # Additional locations
        locations = work.get('locations', [])
        seen_sources = set()

        for location in locations:
            source = location.get('source', {})
            if source:
                source_id = source.get('id', '').replace('https://openalex.org/', '')
                if source_id and source_id not in seen_sources:
                    self.csv_writers['work_sources'].writerow([work_id, source_id])
                    self.stats['work_sources'] += 1
                    seen_sources.add(source_id)

    def extract_citations_by_year(self, work_id: str, work: dict):
        """Extract citations by year"""
        counts_by_year = work.get('counts_by_year', [])

        for entry in counts_by_year:
            year = entry.get('year')
            count = entry.get('cited_by_count')

            if year and count is not None:
                self.csv_writers['citations_by_year'].writerow([
                    work_id,
                    year,
                    count
                ])

                self.stats['citations_by_year'] += 1

    def extract_referenced_works(self, work_id: str, work: dict):
        """Extract referenced works (bibliography)"""
        referenced_works = work.get('referenced_works', [])

        for ref_work_url in referenced_works:
            ref_work_id = ref_work_url.replace('https://openalex.org/', '')
            if ref_work_id:
                self.csv_writers['referenced_works'].writerow([
                    work_id,
                    ref_work_id
                ])

                self.stats['referenced_works'] += 1

    def extract_related_works(self, work_id: str, work: dict):
        """Extract related works"""
        related_works = work.get('related_works', [])

        for rel_work_url in related_works:
            rel_work_id = rel_work_url.replace('https://openalex.org/', '')
            if rel_work_id:
                self.csv_writers['related_works'].writerow([
                    work_id,
                    rel_work_id
                ])

                self.stats['related_works'] += 1

    def extract_alternate_ids(self, work_id: str, work: dict):
        """Extract alternate IDs"""
        ids = work.get('ids', {})

        for id_type, id_value in ids.items():
            if id_value and id_type != 'openalex':  # Don't duplicate the primary ID
                # Clean URL prefixes
                if isinstance(id_value, str):
                    id_value = id_value.replace('https://openalex.org/', '')
                    id_value = id_value.replace('https://doi.org/', '')
                    id_value = id_value.replace('https://www.wikidata.org/entity/', '')

                self.csv_writers['alternate_ids'].writerow([
                    work_id,
                    id_type,
                    id_value
                ])

                self.stats['alternate_ids'] += 1

    def extract_work_keywords(self, work_id: str, work: dict):
        """Extract work keywords"""
        keywords = work.get('keywords', [])

        for keyword in keywords:
            if isinstance(keyword, dict):
                kw = keyword.get('display_name', '')
            else:
                kw = str(keyword)

            if kw:
                self.csv_writers['work_keywords'].writerow([
                    work_id,
                    kw
                ])

                self.stats['work_keywords'] += 1

    def extract_work_funders(self, work_id: str, work: dict):
        """Extract work-funder relationships from grants"""
        grants = work.get('grants', [])

        for grant in grants:
            funder = grant.get('funder')
            if funder:
                funder_id = funder.replace('https://openalex.org/', '')
                award_id = grant.get('award_id')

                if funder_id:
                    self.csv_writers['work_funders'].writerow([
                        work_id,
                        funder_id,
                        award_id
                    ])

                    self.stats['work_funders'] += 1

    def extract_apc(self, work_id: str, work: dict):
        """Extract APC (Article Processing Charge) data"""
        apc_list = work.get('apc_list')
        apc_paid = work.get('apc_paid')

        # Use apc_paid if available, otherwise apc_list
        apc_data = apc_paid or apc_list

        if apc_data:
            self.csv_writers['apc'].writerow([
                work_id,
                apc_data.get('value'),
                apc_data.get('currency'),
                apc_data.get('value_usd'),
                apc_data.get('provenance')
            ])

            self.stats['apc'] += 1

    def extract_work(self, work: dict):
        """Extract all relationships for a single work"""
        work_id = work.get('id', '').replace('https://openalex.org/', '')
        if not work_id:
            return

        try:
            # Extract all relationship types
            self.extract_authorship(work_id, work)
            self.extract_work_topics(work_id, work)
            self.extract_work_concepts(work_id, work)
            self.extract_work_sources(work_id, work)
            self.extract_citations_by_year(work_id, work)
            self.extract_referenced_works(work_id, work)
            self.extract_related_works(work_id, work)
            self.extract_alternate_ids(work_id, work)
            self.extract_work_keywords(work_id, work)
            self.extract_work_funders(work_id, work)
            self.extract_apc(work_id, work)

            self.stats['works_processed'] += 1

        except Exception as e:
            self.logger.error(f"Error extracting relationships for {work_id}: {e}")
            self.stats['errors'] += 1

    def process(self):
        """Main processing loop"""
        try:
            self.setup_csv_writers()

            with gzip.open(self.input_file, 'rt', encoding='utf-8') as f:
                for line_number, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        work = json.loads(line)
                        self.extract_work(work)

                    except json.JSONDecodeError as e:
                        self.logger.warning(f"⚠️  JSON error at line {line_number}: {e}")
                        self.stats['errors'] += 1
                        continue

                    except Exception as e:
                        self.logger.error(f"❌ Error at line {line_number}: {e}")
                        self.stats['errors'] += 1
                        continue

                    # Progress update
                    if self.stats['works_processed'] % PROGRESS_INTERVAL == 0:
                        self.monitor.update(self.stats['works_processed'], 0)

            # Final report
            self.monitor.final_report()
            self.logger.info("\n" + "=" * 60)
            self.logger.info("EXTRACTION SUMMARY")
            self.logger.info("=" * 60)
            self.logger.info(f"Works processed: {self.stats['works_processed']:,}")
            self.logger.info(f"\nRelationships extracted:")
            for table_name in ['authorship', 'work_topics', 'work_concepts', 'work_sources',
                             'citations_by_year', 'referenced_works', 'related_works',
                             'alternate_ids', 'work_keywords', 'work_funders', 'apc']:
                count = self.stats[table_name]
                self.logger.info(f"  {table_name:25s}: {count:,}")

            total_relationships = sum(self.stats[k] for k in self.stats if k not in ['works_processed', 'errors'])
            self.logger.info(f"\nTotal relationships: {total_relationships:,}")
            self.logger.info(f"Errors: {self.stats['errors']:,}")

            return True

        except KeyboardInterrupt:
            self.logger.warning("⚠️  Interrupted by user")
            return False

        except Exception as e:
            self.logger.error(f"❌ FATAL ERROR: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            # Close all CSV files
            for csv_file in self.csv_files.values():
                csv_file.close()

def main():
    parser = argparse.ArgumentParser(description="Extract work relationships to CSV")
    parser.add_argument('--input-file', required=True, help="Input .gz file")
    parser.add_argument('--output-dir', default=str(CSV_OUTPUT_DIR),
                       help=f"Output directory for CSV files (default: {CSV_OUTPUT_DIR})")

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    extractor = RelationshipExtractor(args.input_file, output_dir)
    success = extractor.process()

    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()

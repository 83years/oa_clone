#!/usr/bin/env python3
"""
Parse OpenAlex Works - Phase 1: Main table only
Extracts works from JSON and loads via COPY into works table
"""
import json
import gzip
import psycopg2
import argparse
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import DB_CONFIG
from utils import BatchWriter, setup_logging, get_file_info, PerformanceMonitor

BATCH_SIZE = 100000
PROGRESS_INTERVAL = 5000

class WorksParser:
    """Parse works JSON and load into works table only"""
    
    def __init__(self, input_file: str, mode: str = 'clean'):
        self.input_file = input_file
        self.mode = mode
        
        # Setup logging
        self.logger, self.log_file = setup_logging("parse_works")
        self.logger.info(f"Starting works parser for {input_file}")
        self.logger.info(f"Mode: {mode.upper()}")
        
        # Performance monitoring
        self.monitor = PerformanceMonitor(self.logger, report_interval=PROGRESS_INTERVAL)
        file_info = get_file_info(input_file)
        self.logger.info(f"File size: {file_info['file_size_mb']:.1f} MB")
        if file_info['line_count_estimate']:
            self.logger.info(f"Estimated lines: {file_info['line_count_estimate']:,}")
            self.monitor.set_estimated_total(file_info['line_count_estimate'])
        
        # Database
        self.conn = None
        self.writer = None
        
        # Stats
        self.unique_ids = set()
        self.duplicate_count = 0
        self.error_count = 0
        
    def setup_database(self):
        """Connect to database and setup writer"""
        self.logger.info("Connecting to database...")
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.conn.autocommit = False
        
        # Single writer for works table
        self.writer = BatchWriter(
            self.conn, 'works',
            ['work_id', 'display_name', 'title', 'abstract', 'doi',
             'publication_date', 'publication_year', 'type',
             'is_oa_anywhere', 'oa_status', 'oa_url', 'any_repository_has_fulltext',
             'source_display_name', 'host_organization', 'host_organization_name',
             'host_organization_lineage', 'landing_page_url', 'license', 'version',
             'referenced_works_count', 'is_retracted', 'language', 'language_id',
             'first_page', 'last_page', 'volume', 'issue',
             'keywords', 'sustainable_development_goals', 'grants',
             'referenced_works_score', 'cited_by_count',
             'created_date', 'updated_date', 'mesh_id', 'search_id',
             'biblio_volume', 'biblio_issue', 'biblio_first_page',
             'biblio_last_page', 'is_paratext',
             'fwci', 'citation_normalized_percentile_value',
             'citation_normalized_percentile_top_1_percent',
             'citation_normalized_percentile_top_10_percent',
             'cited_by_percentile_year_min', 'cited_by_percentile_year_max',
             'type_crossref', 'indexed_in', 'locations_count',
             'authors_count', 'concepts_count', 'topics_count', 'has_fulltext',
             'countries_distinct_count', 'institutions_distinct_count',
             'best_oa_pdf_url', 'best_oa_landing_page_url', 'best_oa_is_oa',
             'best_oa_version', 'best_oa_license',
             'primary_location_is_accepted', 'primary_location_is_published',
             'primary_location_pdf_url'],
            self.logger,
            mode=self.mode
        )
        
    def parse_work(self, work: dict) -> str:
        """Extract work data and add to buffer"""
        work_id = work.get('id', '').replace('https://openalex.org/', '')
        if not work_id:
            return None

        # Check duplicates in this file
        if work_id in self.unique_ids:
            self.duplicate_count += 1
            return None

        # Extract nested data structures
        abstract_idx = work.get('abstract_inverted_index')
        abstract = json.dumps(abstract_idx) if abstract_idx else None

        open_access = work.get('open_access', {})
        primary_location = work.get('primary_location', {})
        source = primary_location.get('source', {}) if primary_location else {}
        biblio = work.get('biblio', {})
        best_oa = work.get('best_oa_location', {})
        citation_norm_percentile = work.get('citation_normalized_percentile', {})
        cited_by_percentile_year = work.get('cited_by_percentile_year', {})

        # Extract type without URL prefix
        work_type = work.get('type', '')
        if work_type.startswith('https://openalex.org/types/'):
            work_type = work_type.replace('https://openalex.org/types/', '')

        # Extract host organization from source
        host_org = source.get('host_organization') if source else None
        if host_org and isinstance(host_org, str):
            host_org_id = host_org.replace('https://openalex.org/', '')
        else:
            host_org_id = None

        # Extract host organization lineage
        host_org_lineage = source.get('host_organization_lineage', []) if source else []
        if isinstance(host_org_lineage, list) and host_org_lineage:
            lineage_str = ','.join([h.replace('https://openalex.org/', '') for h in host_org_lineage if h])
        else:
            lineage_str = None

        # Extract keywords (convert array to comma-separated string)
        keywords_list = work.get('keywords', [])
        keywords_str = ','.join([k.get('display_name', '') for k in keywords_list if isinstance(k, dict)]) if keywords_list else None

        # Extract SDGs (convert array to comma-separated string)
        sdgs = work.get('sustainable_development_goals', [])
        sdgs_str = ','.join([str(s.get('id', '')) for s in sdgs if isinstance(s, dict)]) if sdgs else None

        # Extract grants (convert array to JSON string)
        grants_list = work.get('grants', [])
        grants_str = json.dumps(grants_list) if grants_list else None

        # Extract MeSH terms (convert array to comma-separated string)
        mesh_list = work.get('mesh', [])
        mesh_str = ','.join([m.get('descriptor_ui', '') for m in mesh_list if isinstance(m, dict)]) if mesh_list else None

        # Extract indexed_in (convert array to comma-separated string)
        indexed_in_list = work.get('indexed_in', [])
        indexed_in_str = ','.join(indexed_in_list) if indexed_in_list else None

        # Extract language_id
        language_id = work.get('language_id', '')
        if language_id and language_id.startswith('https://openalex.org/'):
            language_id = language_id.replace('https://openalex.org/languages/', '')

        # Add to buffer
        self.writer.add_record({
            'work_id': work_id,
            'display_name': work.get('display_name', ''),
            'title': work.get('title', ''),
            'abstract': abstract,
            'doi': work.get('doi'),
            'publication_date': work.get('publication_date'),
            'publication_year': work.get('publication_year'),
            'type': work_type,
            'is_oa_anywhere': open_access.get('is_oa', False) if open_access else False,
            'oa_status': open_access.get('oa_status') if open_access else None,
            'oa_url': open_access.get('oa_url') if open_access else None,
            'any_repository_has_fulltext': open_access.get('any_repository_has_fulltext', False) if open_access else False,
            'source_display_name': source.get('display_name') if source else None,
            'host_organization': host_org_id,
            'host_organization_name': source.get('host_organization_name') if source else None,
            'host_organization_lineage': lineage_str,
            'landing_page_url': primary_location.get('landing_page_url') if primary_location else None,
            'license': primary_location.get('license') if primary_location else None,
            'version': primary_location.get('version') if primary_location else None,
            'referenced_works_count': work.get('referenced_works_count', len(work.get('referenced_works', []))),
            'is_retracted': work.get('is_retracted', False),
            'language': work.get('language'),
            'language_id': language_id,
            'first_page': biblio.get('first_page') if biblio else None,
            'last_page': biblio.get('last_page') if biblio else None,
            'volume': biblio.get('volume') if biblio else None,
            'issue': biblio.get('issue') if biblio else None,
            'keywords': keywords_str,
            'sustainable_development_goals': sdgs_str,
            'grants': grants_str,
            'referenced_works_score': None,  # Not in source data
            'cited_by_count': work.get('cited_by_count', 0),
            'created_date': work.get('created_date'),
            'updated_date': work.get('updated_date'),
            'mesh_id': mesh_str,
            'search_id': None,  # For manual searches, not in OpenAlex data
            'biblio_volume': biblio.get('volume') if biblio else None,
            'biblio_issue': biblio.get('issue') if biblio else None,
            'biblio_first_page': biblio.get('first_page') if biblio else None,
            'biblio_last_page': biblio.get('last_page') if biblio else None,
            'is_paratext': work.get('is_paratext', False),
            'fwci': work.get('fwci'),
            'citation_normalized_percentile_value': citation_norm_percentile.get('value') if citation_norm_percentile else None,
            'citation_normalized_percentile_top_1_percent': citation_norm_percentile.get('is_in_top_1_percent') if citation_norm_percentile else None,
            'citation_normalized_percentile_top_10_percent': citation_norm_percentile.get('is_in_top_10_percent') if citation_norm_percentile else None,
            'cited_by_percentile_year_min': cited_by_percentile_year.get('min') if cited_by_percentile_year else None,
            'cited_by_percentile_year_max': cited_by_percentile_year.get('max') if cited_by_percentile_year else None,
            'type_crossref': work.get('type_crossref'),
            'indexed_in': indexed_in_str,
            'locations_count': work.get('locations_count'),
            'authors_count': work.get('authors_count'),
            'concepts_count': work.get('concepts_count'),
            'topics_count': work.get('topics_count'),
            'has_fulltext': work.get('has_fulltext', False),
            'countries_distinct_count': work.get('countries_distinct_count'),
            'institutions_distinct_count': work.get('institutions_distinct_count'),
            'best_oa_pdf_url': best_oa.get('pdf_url') if best_oa else None,
            'best_oa_landing_page_url': best_oa.get('landing_page_url') if best_oa else None,
            'best_oa_is_oa': best_oa.get('is_oa') if best_oa else None,
            'best_oa_version': best_oa.get('version') if best_oa else None,
            'best_oa_license': best_oa.get('license') if best_oa else None,
            'primary_location_is_accepted': primary_location.get('is_accepted') if primary_location else None,
            'primary_location_is_published': primary_location.get('is_published') if primary_location else None,
            'primary_location_pdf_url': primary_location.get('pdf_url') if primary_location else None
        })

        self.unique_ids.add(work_id)

        # Clear unique_ids periodically to prevent memory issues
        if len(self.unique_ids) > 500000:
            self.unique_ids.clear()

        return work_id
    
    def process(self):
        """Main processing loop"""
        try:
            self.setup_database()
            
            records_processed = 0
            batches_completed = 0
            
            with gzip.open(self.input_file, 'rt', encoding='utf-8') as f:
                batch_records = 0
                
                for line_number, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        work = json.loads(line)
                        work_id = self.parse_work(work)
                        
                        if work_id:
                            records_processed += 1
                            batch_records += 1
                            
                    except json.JSONDecodeError as e:
                        self.error_count += 1
                        self.logger.warning(f"⚠️  JSON error at line {line_number}: {e}")
                        continue
                    except Exception as e:
                        self.error_count += 1
                        self.logger.error(f"❌ Error at line {line_number}: {e}")
                        continue
                    
                    # Write batch when full
                    if batch_records >= BATCH_SIZE:
                        self.writer.write_batch()
                        self.conn.commit()
                        batches_completed += 1
                        batch_records = 0
                        self.logger.info(f"✅ Batch {batches_completed} committed")
                    
                    # Progress update
                    if records_processed % PROGRESS_INTERVAL == 0:
                        self.monitor.update(records_processed, batches_completed)
                
                # Write final batch
                if batch_records > 0:
                    self.writer.write_batch()
                    self.conn.commit()
                    batches_completed += 1
                    self.logger.info(f"✅ Final batch committed")
                
                # Final report
                self.monitor.final_report()
                self.logger.info(f"Total works: {records_processed:,}")
                self.logger.info(f"Duplicates: {self.duplicate_count:,}")
                self.logger.info(f"Errors: {self.error_count:,}")
                self.logger.info(f"Batches: {batches_completed}")
                
                return True
                
        except KeyboardInterrupt:
            self.logger.warning("⚠️  Interrupted by user")
            if self.conn:
                self.conn.rollback()
            return False

        except Exception as e:
            self.logger.error(f"❌ FATAL ERROR: {e}")
            if self.conn:
                self.conn.rollback()
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            if self.conn:
                self.conn.close()

def main():
    parser = argparse.ArgumentParser(description="Parse OpenAlex works - Phase 1")
    parser.add_argument('--input-file', required=True, help="Input .gz file")
    parser.add_argument('--mode', choices=['clean', 'update'], default='clean',
                       help="Processing mode")
    
    args = parser.parse_args()
    
    processor = WorksParser(args.input_file, mode=args.mode)
    success = processor.process()
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()

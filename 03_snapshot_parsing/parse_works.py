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
             'referenced_works_count', 'is_retracted', 'language', 
             'first_page', 'last_page', 'volume', 'issue',
             'keywords', 'sustainable_development_goals', 'grants',
             'referenced_works_score', 'cited_by_count', 
             'created_date', 'updated_date', 'mesh_id', 'search_id',
             'biblio_volume', 'biblio_issue', 'biblio_first_page', 
             'biblio_last_page', 'is_paratext'],
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
        
        # Extract data
        abstract_idx = work.get('abstract_inverted_index')
        abstract = json.dumps(abstract_idx) if abstract_idx else None
        
        open_access = work.get('open_access', {})
        primary_location = work.get('primary_location', {})
        source = primary_location.get('source', {}) if primary_location else {}
        biblio = work.get('biblio', {})
        
        # Extract type without URL prefix
        work_type = work.get('type', '')
        if work_type.startswith('https://openalex.org/types/'):
            work_type = work_type.replace('https://openalex.org/types/', '')
        
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
            'host_organization': source.get('host_organization') if source else None,
            'host_organization_name': None,
            'host_organization_lineage': None,
            'landing_page_url': primary_location.get('landing_page_url') if primary_location else None,
            'license': primary_location.get('license') if primary_location else None,
            'version': primary_location.get('version') if primary_location else None,
            'referenced_works_count': len(work.get('referenced_works', [])),
            'is_retracted': work.get('is_retracted', False),
            'language': work.get('language'),
            'first_page': biblio.get('first_page') if biblio else None,
            'last_page': biblio.get('last_page') if biblio else None,
            'volume': biblio.get('volume') if biblio else None,
            'issue': biblio.get('issue') if biblio else None,
            'keywords': None,
            'sustainable_development_goals': None,
            'grants': None,
            'referenced_works_score': None,
            'cited_by_count': work.get('cited_by_count', 0),
            'created_date': work.get('created_date'),
            'updated_date': work.get('updated_date'),
            'mesh_id': None,
            'search_id': None,
            'biblio_volume': None,
            'biblio_issue': None,
            'biblio_first_page': None,
            'biblio_last_page': None,
            'is_paratext': None
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

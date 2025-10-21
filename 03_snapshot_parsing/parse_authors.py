#!/usr/bin/env python3
"""
Parse OpenAlex Authors - ETL Best Practice Version
Assumes database is pre-configured by orchestrator
"""
import json
import gzip
import psycopg2
import argparse
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from config import DB_CONFIG
from utils import (
    BatchWriter, setup_logging, get_file_info,
    generate_job_id, PerformanceMonitor
)

# Configuration - optimized for bulk loading
BATCH_SIZE = 100000
PROGRESS_INTERVAL = 10000

class AuthorsParser:
    """Streaming parser for OpenAlex authors data"""
    
    def __init__(self, input_file: str, mode: str = 'clean'):
        self.input_file = input_file
        self.mode = mode  # 'clean' or 'update'
        self.entity_type = "authors"
        
        # Setup logging
        self.logger, self.log_file = setup_logging(f"parse_{self.entity_type}")
        self.logger.info(f"Starting {self.entity_type} parser for {input_file}")
        self.logger.info(f"Mode: {mode.upper()}")
        
        # Setup performance monitor
        self.monitor = PerformanceMonitor(self.logger, report_interval=PROGRESS_INTERVAL)
        
        # Get file info for estimation
        file_info = get_file_info(input_file)
        self.logger.info(f"File size: {file_info['file_size_mb']:.1f} MB")
        if file_info['line_count_estimate']:
            self.logger.info(f"Estimated lines: {file_info['line_count_estimate']:,}")
            self.monitor.set_estimated_total(file_info['line_count_estimate'])
        
        # Database connection
        self.conn = None
        self.writers = {}
        
        # Processing state
        self.unique_ids = set()
        self.error_count = 0
        self.duplicate_count = 0
        
    def setup_database(self):
        """Setup database connection and writers"""
        self.logger.info("Connecting to database...")
        self.conn = psycopg2.connect(**DB_CONFIG)
        self.conn.autocommit = False
        
        # Setup batch writers for all tables
        self.writers = {
            'authors': BatchWriter(
                self.conn, 'authors',
                ['author_id', 'display_name', 'orcid', 'works_count', 'cited_by_count',
                 'summary_stats_2yr_mean_citedness', 'summary_stats_h_index', 
                 'summary_stats_i10_index', 'created_date', 'updated_date', 'gender',
                 'current_affiliation_id', 'current_affiliation_name', 
                 'current_affiliation_country', 'current_affiliation_type',
                 'api_response_date', 'api_source', 'most_cited_work', 
                 'first_publication_year', 'last_publication_year',
                 'freq_corresponding_author', 'total_works', 'total_citations',
                 'corresponding_authorships', 'career_length_years', 'current',
                 'career_stage_aff'],
                self.logger,
                mode=self.mode
            ),
            'author_topics': BatchWriter(
                self.conn, 'author_topics',
                ['author_id', 'topic_id', 'score', 'work_count', 'recent_work_count'],
                self.logger,
                mode=self.mode
            ),
            'author_concepts': BatchWriter(
                self.conn, 'author_concepts',
                ['author_id', 'concept_id', 'score', 'work_count'],
                self.logger,
                mode=self.mode
            ),
            'author_name_variants': BatchWriter(
                self.conn, 'author_name_variants',
                ['author_id', 'name_variant', 'variant_type', 'confidence_score'],
                self.logger,
                mode=self.mode
            ),
            'authors_works_by_year': BatchWriter(
                self.conn, 'authors_works_by_year',
                ['author_id', 'year', 'works_count', 'oa_works_count', 'cited_by_count'],
                self.logger,
                mode=self.mode
            ),
            'author_institutions': BatchWriter(
                self.conn, 'author_institutions',
                ['author_id', 'institution_id', 'start_date', 'end_date'],
                self.logger,
                mode=self.mode
            )
        }
        
    def parse_author(self, author: Dict[str, Any]) -> Optional[str]:
        """Parse single author record and add to batches"""
        author_id = author.get('id', '').replace('https://openalex.org/', '')
        if not author_id:
            return None
        
        # Check for duplicates within this file
        if author_id in self.unique_ids:
            self.duplicate_count += 1
            return None
        
        # Main author record
        ids = author.get('ids', {})
        orcid = ids.get('orcid', '').replace('https://orcid.org/', '') if ids else None
        
        summary_stats = author.get('summary_stats', {})
        
        # Extract current affiliation
        last_known = author.get('last_known_institutions', [])
        current_affiliation_id = None
        current_affiliation_name = None
        current_affiliation_country = None
        current_affiliation_type = None
        
        if last_known and len(last_known) > 0:
            first_inst = last_known[0]
            current_affiliation_id = first_inst.get('id', '').replace('https://openalex.org/', '') or None
            current_affiliation_name = first_inst.get('display_name')
            current_affiliation_country = first_inst.get('country_code')
            current_affiliation_type = first_inst.get('type')
        
        self.writers['authors'].add_record({
            'author_id': author_id,
            'display_name': author.get('display_name', ''),
            'orcid': orcid,
            'works_count': summary_stats.get('works_count') if summary_stats else None,
            'cited_by_count': summary_stats.get('cited_by_count') if summary_stats else None,
            'summary_stats_2yr_mean_citedness': summary_stats.get('2yr_mean_citedness') if summary_stats else None,
            'summary_stats_h_index': summary_stats.get('h_index') if summary_stats else None,
            'summary_stats_i10_index': summary_stats.get('i10_index') if summary_stats else None,
            'created_date': author.get('created_date'),
            'updated_date': author.get('updated_date'),
            'gender': author.get('gender'),
            'current_affiliation_id': current_affiliation_id,
            'current_affiliation_name': current_affiliation_name,
            'current_affiliation_country': current_affiliation_country,
            'current_affiliation_type': current_affiliation_type,
            'api_response_date': None,
            'api_source': None,
            'most_cited_work': None,
            'first_publication_year': None,
            'last_publication_year': None,
            'freq_corresponding_author': None,
            'total_works': None,
            'total_citations': None,
            'corresponding_authorships': None,
            'career_length_years': None,
            'current': None,
            'career_stage_aff': None
        })
        
        # Topics
        for topic in author.get('topics', []):
            if topic:
                topic_id = topic.get('id', '').replace('https://openalex.org/', '')
                if topic_id:
                    self.writers['author_topics'].add_record({
                        'author_id': author_id,
                        'topic_id': topic_id,
                        'score': topic.get('value'),
                        'work_count': topic.get('count'),
                        'recent_work_count': None
                    })
        
        # Concepts
        for concept in author.get('x_concepts', []):
            if concept:
                concept_id = concept.get('id', '').replace('https://openalex.org/', '')
                if concept_id:
                    self.writers['author_concepts'].add_record({
                        'author_id': author_id,
                        'concept_id': concept_id,
                        'score': concept.get('score'),
                        'work_count': None
                    })
        
        # Name variants
        for variant in author.get('display_name_alternatives', []):
            if variant:
                self.writers['author_name_variants'].add_record({
                    'author_id': author_id,
                    'name_variant': variant,
                    'variant_type': 'alternative_name',
                    'confidence_score': None
                })
        
        # Works by year
        for year_data in author.get('counts_by_year', []):
            if year_data:
                self.writers['authors_works_by_year'].add_record({
                    'author_id': author_id,
                    'year': year_data.get('year'),
                    'works_count': year_data.get('works_count'),
                    'oa_works_count': year_data.get('oa_works_count'),
                    'cited_by_count': year_data.get('cited_by_count')
                })
        
        # Author institutions
        for affiliation in author.get('affiliations', []):
            if affiliation:
                institution = affiliation.get('institution', {})
                if institution:
                    institution_id = institution.get('id', '').replace('https://openalex.org/', '')
                    years = affiliation.get('years', [])
                    
                    if institution_id and years:
                        # Validate and convert years
                        valid_years = []
                        for year in years:
                            if isinstance(year, int) and year > 0:
                                # Handle 2-digit years: assume 1900s if > 50, else 2000s
                                if year < 100:
                                    year = 1900 + year if year > 50 else 2000 + year
                                # Only accept reasonable years (1000-2100)
                                if 1000 <= year <= 2100:
                                    valid_years.append(year)
                        
                        if valid_years:
                            min_year = min(valid_years)
                            max_year = max(valid_years)
                            self.writers['author_institutions'].add_record({
                                'author_id': author_id,
                                'institution_id': institution_id,
                                'start_date': f"{min_year}-01-01",
                                'end_date': f"{max_year}-12-31"
                            })
        
        self.unique_ids.add(author_id)
        return author_id
    
    def write_batch(self):
        """Write all buffers to database"""
        start_time = time.time()
        total_written = 0
        
        for table_name, writer in self.writers.items():
            if writer.buffer:
                count = writer.write_batch()
                total_written += count
        
        elapsed = time.time() - start_time
        self.logger.debug(f"Batch write: {total_written} records in {elapsed:.2f}s")
        return total_written
    
    def process(self):
        """Main processing loop"""
        try:
            self.setup_database()
            
            line_number = 0
            records_processed = 0
            batches_completed = 0
            
            with gzip.open(self.input_file, 'rt', encoding='utf-8') as f:
                batch_records = 0
                
                while True:
                    line = f.readline()
                    if not line:
                        break
                    
                    line_number += 1
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Parse JSON
                    try:
                        author = json.loads(line)
                        author_id = self.parse_author(author)
                        
                        if author_id:
                            records_processed += 1
                            batch_records += 1
                            
                    except json.JSONDecodeError as e:
                        self.error_count += 1
                        self.logger.warning(f"JSON error at line {line_number}: {e}")
                        continue
                    except Exception as e:
                        self.error_count += 1
                        self.logger.error(f"Error at line {line_number}: {e}")
                        continue
                    
                    # Write batch if size reached
                    if batch_records >= BATCH_SIZE:
                        self.write_batch()
                        self.conn.commit()
                        batches_completed += 1
                        batch_records = 0
                    
                    # Update progress
                    if records_processed % PROGRESS_INTERVAL == 0:
                        self.monitor.update(records_processed, batches_completed)
                
                # Write final batch
                if batch_records > 0:
                    self.write_batch()
                    self.conn.commit()
                    batches_completed += 1
                
                # Final report
                self.monitor.final_report()
                self.logger.info(f"Total authors: {records_processed:,}")
                self.logger.info(f"Duplicates in file: {self.duplicate_count:,}")
                self.logger.info(f"Errors: {self.error_count:,}")
                self.logger.info(f"Batches: {batches_completed}")
                
                return True
                
        except KeyboardInterrupt:
            self.logger.warning("Processing interrupted by user")
            if self.conn:
                self.conn.rollback()
            return False
            
        except Exception as e:
            self.logger.error(f"FATAL ERROR: {e}")
            if self.conn:
                self.conn.rollback()
            import traceback
            traceback.print_exc()
            return False
            
        finally:
            if self.conn:
                self.conn.close()

def main():
    parser = argparse.ArgumentParser(description="Parse OpenAlex authors data")
    parser.add_argument('--input-file', required=True, help="Input .gz file")
    parser.add_argument('--mode', choices=['clean', 'update'], default='clean',
                       help="Processing mode")
    
    args = parser.parse_args()
    
    processor = AuthorsParser(args.input_file, mode=args.mode)
    success = processor.process()
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
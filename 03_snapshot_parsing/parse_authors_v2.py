#!/usr/bin/env python3
"""
Parse OpenAlex Authors - Version 2 with COPY support
Populates: authors, author_topics, author_concepts, author_institutions, authors_works_by_year
"""
import json
import time
import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from base_parser import BaseParser


class AuthorsParser(BaseParser):
    """Parser for authors and all related tables"""

    def __init__(self, input_file, line_limit=None):
        super().__init__('authors', input_file, line_limit)

        # Column definitions for all tables
        self.authors_columns = [
            'author_id', 'display_name', 'orcid', 'works_count', 'cited_by_count',
            'summary_stats_2yr_mean_citedness', 'summary_stats_h_index', 'summary_stats_i10_index',
            'created_date', 'updated_date', 'current_affiliation_id', 'current_affiliation_name',
            'current_affiliation_country', 'current_affiliation_type'
        ]

        self.author_topics_columns = [
            'author_id', 'topic_id', 'score', 'work_count', 'recent_work_count'
        ]

        self.author_concepts_columns = [
            'author_id', 'concept_id', 'score', 'work_count'
        ]

        self.author_institutions_columns = [
            'author_id', 'institution_id', 'start_date', 'end_date', 'affiliation_string'
        ]

        self.authors_works_by_year_columns = [
            'author_id', 'year', 'works_count', 'oa_works_count', 'cited_by_count'
        ]

    def parse(self):
        """Main parsing logic"""
        self.stats['start_time'] = time.time()
        self.connect_db()

        # Batches for each table
        authors_batch = []
        author_topics_batch = []
        author_concepts_batch = []
        author_institutions_batch = []
        authors_works_by_year_batch = []
        unique_ids = set()

        try:
            for author in self.read_gz_stream():
                author_id = self.clean_openalex_id(author.get('id'))
                if not author_id or author_id in unique_ids:
                    continue

                unique_ids.add(author_id)

                # Clean ORCID
                orcid = author.get('orcid', '')
                if orcid:
                    orcid = orcid.replace('https://orcid.org/', '')

                # Extract summary stats
                summary_stats = author.get('summary_stats', {}) or {}

                # Extract last known institution (for current affiliation)
                last_known_institutions = author.get('last_known_institutions', [])
                current_aff_id = None
                current_aff_name = None
                current_aff_country = None
                current_aff_type = None

                if last_known_institutions and len(last_known_institutions) > 0:
                    current_aff = last_known_institutions[0]
                    current_aff_id = self.clean_openalex_id(current_aff.get('id'))
                    current_aff_name = current_aff.get('display_name')
                    current_aff_country = current_aff.get('country_code')
                    aff_type = current_aff.get('type')
                    current_aff_type = aff_type.replace('https://openalex.org/institution-types/', '') if aff_type else None

                # Main author record
                authors_batch.append({
                    'author_id': author_id,
                    'display_name': author.get('display_name'),
                    'orcid': orcid if orcid else None,
                    'works_count': author.get('works_count'),
                    'cited_by_count': author.get('cited_by_count'),
                    'summary_stats_2yr_mean_citedness': summary_stats.get('2yr_mean_citedness'),
                    'summary_stats_h_index': summary_stats.get('h_index'),
                    'summary_stats_i10_index': summary_stats.get('i10_index'),
                    'created_date': author.get('created_date'),
                    'updated_date': author.get('updated_date'),
                    'current_affiliation_id': current_aff_id,
                    'current_affiliation_name': current_aff_name,
                    'current_affiliation_country': current_aff_country,
                    'current_affiliation_type': current_aff_type
                })

                # Author topics
                topics = author.get('topics', [])
                for topic in topics:
                    topic_id = self.clean_openalex_id(topic.get('id'))
                    if topic_id:
                        author_topics_batch.append({
                            'author_id': author_id,
                            'topic_id': topic_id,
                            'score': topic.get('score'),
                            'work_count': topic.get('count'),
                            'recent_work_count': None  # Not in current API
                        })

                # Author concepts (x_concepts in API)
                x_concepts = author.get('x_concepts', [])
                for concept in x_concepts:
                    concept_id = self.clean_openalex_id(concept.get('id'))
                    if concept_id:
                        author_concepts_batch.append({
                            'author_id': author_id,
                            'concept_id': concept_id,
                            'score': concept.get('score'),
                            'work_count': concept.get('count')
                        })

                # Author institutions (affiliations)
                affiliations = author.get('affiliations', [])
                for affiliation in affiliations:
                    institution = affiliation.get('institution', {})
                    if not institution:
                        continue

                    inst_id = self.clean_openalex_id(institution.get('id'))
                    if inst_id:
                        years = affiliation.get('years', [])
                        start_year = min(years) if years else None
                        end_year = max(years) if years else None

                        author_institutions_batch.append({
                            'author_id': author_id,
                            'institution_id': inst_id,
                            'start_date': f"{start_year}-01-01" if start_year else None,
                            'end_date': f"{end_year}-12-31" if end_year else None,
                            'affiliation_string': institution.get('display_name')
                        })

                # Works by year
                counts_by_year = author.get('counts_by_year', [])
                for count in counts_by_year:
                    year = count.get('year')
                    if year:
                        authors_works_by_year_batch.append({
                            'author_id': author_id,
                            'year': year,
                            'works_count': count.get('works_count'),
                            'oa_works_count': count.get('oa_works_count'),
                            'cited_by_count': count.get('cited_by_count')
                        })

                self.stats['records_parsed'] += 1

                # Batch writes
                if len(authors_batch) >= 50000:
                    self.write_with_copy('authors', authors_batch, self.authors_columns)
                    authors_batch = []

                if len(author_topics_batch) >= 50000:
                    self.write_with_copy('author_topics', author_topics_batch, self.author_topics_columns)
                    author_topics_batch = []

                if len(author_concepts_batch) >= 50000:
                    self.write_with_copy('author_concepts', author_concepts_batch, self.author_concepts_columns)
                    author_concepts_batch = []

                if len(author_institutions_batch) >= 50000:
                    self.write_with_copy('author_institutions', author_institutions_batch, self.author_institutions_columns)
                    author_institutions_batch = []

                if len(authors_works_by_year_batch) >= 50000:
                    self.write_with_copy('authors_works_by_year', authors_works_by_year_batch, self.authors_works_by_year_columns)
                    authors_works_by_year_batch = []

            # Write remaining records
            if authors_batch:
                self.write_with_copy('authors', authors_batch, self.authors_columns)
            if author_topics_batch:
                self.write_with_copy('author_topics', author_topics_batch, self.author_topics_columns)
            if author_concepts_batch:
                self.write_with_copy('author_concepts', author_concepts_batch, self.author_concepts_columns)
            if author_institutions_batch:
                self.write_with_copy('author_institutions', author_institutions_batch, self.author_institutions_columns)
            if authors_works_by_year_batch:
                self.write_with_copy('authors_works_by_year', authors_works_by_year_batch, self.authors_works_by_year_columns)

        finally:
            self.stats['end_time'] = time.time()
            self.close_db()
            self.print_stats()

        return self.stats


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Parse OpenAlex authors with COPY')
    parser.add_argument('--input-file', required=True, help='Path to authors .gz file')
    parser.add_argument('--limit', type=int, help='Limit number of lines (testing)')
    args = parser.parse_args()

    try:
        authors_parser = AuthorsParser(args.input_file, line_limit=args.limit)
        stats = authors_parser.parse()
        sys.exit(0 if stats['errors'] == 0 else 1)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

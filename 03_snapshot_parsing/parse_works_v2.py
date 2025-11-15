#!/usr/bin/env python3
"""
Parse OpenAlex Works - Version 2 with COPY support
Populates: works, authorship, work_topics, work_concepts, work_sources,
           work_keywords, work_funders, citations_by_year, referenced_works, related_works
"""
import json
import time
import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from base_parser import BaseParser


class WorksParser(BaseParser):
    """Parser for works and all related tables including authorship"""

    def __init__(self, input_file, line_limit=None):
        super().__init__('works', input_file, line_limit)

        # Column definitions for all tables
        self.works_columns = [
            'work_id', 'display_name', 'title', 'abstract', 'doi', 'publication_date',
            'publication_year', 'type', 'is_oa_anywhere', 'oa_status', 'oa_url',
            'any_repository_has_fulltext', 'source_display_name', 'host_organization',
            'host_organization_name', 'host_organization_lineage', 'landing_page_url',
            'license', 'version', 'referenced_works_count', 'is_retracted', 'language',
            'language_id', 'first_page', 'last_page', 'volume', 'issue', 'keywords',
            'sustainable_development_goals', 'grants', 'referenced_works_score',
            'cited_by_count', 'created_date', 'updated_date', 'mesh_id', 'search_id',
            'biblio_volume', 'biblio_issue', 'biblio_first_page', 'biblio_last_page',
            'is_paratext', 'fwci', 'citation_normalized_percentile_value',
            'citation_normalized_percentile_top_1_percent', 'citation_normalized_percentile_top_10_percent',
            'cited_by_percentile_year_min', 'cited_by_percentile_year_max', 'type_crossref',
            'indexed_in', 'locations_count', 'authors_count', 'concepts_count', 'topics_count',
            'has_fulltext', 'countries_distinct_count', 'institutions_distinct_count',
            'best_oa_pdf_url', 'best_oa_landing_page_url', 'best_oa_is_oa', 'best_oa_version',
            'best_oa_license', 'primary_location_is_accepted', 'primary_location_is_published',
            'primary_location_pdf_url'
        ]

        self.authorship_columns = [
            'work_id', 'author_id', 'author_position', 'is_corresponding',
            'raw_affiliation_string', 'institution_id'
        ]

        self.work_topics_columns = ['work_id', 'topic_id', 'score', 'is_primary_topic']
        self.work_concepts_columns = ['work_id', 'concept_id', 'score']
        self.work_sources_columns = ['work_id', 'source_id']
        self.work_keywords_columns = ['work_id', 'keyword']
        self.work_funders_columns = ['work_id', 'funder_id', 'award_id']
        self.citations_by_year_columns = ['work_id', 'year', 'citation_count']
        self.referenced_works_columns = ['work_id', 'referenced_work_id']
        self.related_works_columns = ['work_id', 'related_work_id']
        self.apc_columns = ['work_id', 'value', 'currency', 'value_usd', 'provenance']

    def parse(self):
        """Main parsing logic"""
        self.stats['start_time'] = time.time()
        self.connect_db()

        # Batches for each table
        works_batch = []
        authorship_batch = []
        work_topics_batch = []
        work_concepts_batch = []
        work_sources_batch = []
        work_keywords_batch = []
        work_funders_batch = []
        citations_by_year_batch = []
        referenced_works_batch = []
        related_works_batch = []
        apc_batch = []

        unique_ids = set()

        try:
            for work in self.read_gz_stream():
                work_id = self.clean_openalex_id(work.get('id'))
                if not work_id or work_id in unique_ids:
                    continue

                unique_ids.add(work_id)

                # Extract open access info
                oa_info = work.get('open_access', {}) or {}
                best_oa = work.get('best_oa_location', {}) or {}
                primary_location = work.get('primary_location', {}) or {}
                biblio = work.get('biblio', {}) or {}

                # Extract host organization info from primary location
                primary_source = primary_location.get('source', {}) or {}
                host_org = None
                host_org_name = None
                host_org_lineage = None
                source_display_name = primary_source.get('display_name') if primary_source else None

                if primary_source and primary_source.get('host_organization'):
                    host_org = self.clean_openalex_id(primary_source.get('host_organization'))
                    host_org_name = primary_source.get('host_organization_name')
                    host_org_lineage = primary_source.get('host_organization_lineage')

                # Convert arrays to text
                keywords_list = work.get('keywords')
                keywords_str = json.dumps([k.get('keyword') for k in keywords_list]) if keywords_list else None

                sdgs = work.get('sustainable_development_goals')
                sdgs_str = json.dumps(sdgs) if sdgs else None

                grants = work.get('grants')
                grants_str = json.dumps(grants) if grants else None

                indexed_in = work.get('indexed_in')
                indexed_str = json.dumps(indexed_in) if indexed_in else None

                # Abstract handling
                abstract_inverted = work.get('abstract_inverted_index')
                abstract_text = None
                if abstract_inverted:
                    # Reconstruct abstract from inverted index
                    words = []
                    for word, positions in abstract_inverted.items():
                        for pos in positions:
                            words.append((pos, word))
                    words.sort()
                    abstract_text = ' '.join([w[1] for w in words])

                # Main work record
                works_batch.append({
                    'work_id': work_id,
                    'display_name': work.get('display_name'),
                    'title': work.get('title'),
                    'abstract': abstract_text,
                    'doi': work.get('doi'),
                    'publication_date': work.get('publication_date'),
                    'publication_year': work.get('publication_year'),
                    'type': work.get('type'),
                    'is_oa_anywhere': oa_info.get('is_oa'),
                    'oa_status': oa_info.get('oa_status'),
                    'oa_url': oa_info.get('oa_url'),
                    'any_repository_has_fulltext': oa_info.get('any_repository_has_fulltext'),
                    'source_display_name': source_display_name,
                    'host_organization': host_org,
                    'host_organization_name': host_org_name,
                    'host_organization_lineage': host_org_lineage,
                    'landing_page_url': work.get('landing_page_url') or primary_location.get('landing_page_url'),
                    'license': primary_location.get('license'),
                    'version': primary_location.get('version'),
                    'referenced_works_count': len(work.get('referenced_works', [])),
                    'is_retracted': work.get('is_retracted'),
                    'language': work.get('language'),
                    'language_id': self.clean_openalex_id(work.get('language_id')),
                    'first_page': biblio.get('first_page'),
                    'last_page': biblio.get('last_page'),
                    'volume': biblio.get('volume'),
                    'issue': biblio.get('issue'),
                    'keywords': keywords_str,
                    'sustainable_development_goals': sdgs_str,
                    'grants': grants_str,
                    'referenced_works_score': None,  # Not in current API
                    'cited_by_count': work.get('cited_by_count'),
                    'created_date': work.get('created_date'),
                    'updated_date': work.get('updated_date'),
                    'mesh_id': None,  # Not in current API
                    'search_id': None,  # Set by search process
                    'biblio_volume': biblio.get('volume'),
                    'biblio_issue': biblio.get('issue'),
                    'biblio_first_page': biblio.get('first_page'),
                    'biblio_last_page': biblio.get('last_page'),
                    'is_paratext': work.get('is_paratext'),
                    'fwci': None,  # Not in current API
                    'citation_normalized_percentile_value': None,  # Not in current API
                    'citation_normalized_percentile_top_1_percent': None,
                    'citation_normalized_percentile_top_10_percent': None,
                    'cited_by_percentile_year_min': None,
                    'cited_by_percentile_year_max': None,
                    'type_crossref': work.get('type_crossref'),
                    'indexed_in': indexed_str,
                    'locations_count': len(work.get('locations', [])),
                    'authors_count': len(work.get('authorships', [])),
                    'concepts_count': len(work.get('concepts', [])),
                    'topics_count': len(work.get('topics', [])),
                    'has_fulltext': work.get('has_fulltext'),
                    'countries_distinct_count': work.get('countries_distinct_count'),
                    'institutions_distinct_count': work.get('institutions_distinct_count'),
                    'best_oa_pdf_url': best_oa.get('pdf_url'),
                    'best_oa_landing_page_url': best_oa.get('landing_page_url'),
                    'best_oa_is_oa': best_oa.get('is_oa'),
                    'best_oa_version': best_oa.get('version'),
                    'best_oa_license': best_oa.get('license'),
                    'primary_location_is_accepted': primary_location.get('is_accepted'),
                    'primary_location_is_published': primary_location.get('is_published'),
                    'primary_location_pdf_url': primary_location.get('pdf_url')
                })

                # Authorships - CRITICAL: One row per author per institution
                authorships = work.get('authorships', [])
                for authorship in authorships:
                    author = authorship.get('author', {}) or {}
                    author_id = self.clean_openalex_id(author.get('id'))

                    if not author_id:
                        continue

                    author_position = authorship.get('author_position')
                    is_corresponding = authorship.get('is_corresponding')

                    # Get raw affiliation strings
                    raw_affs = authorship.get('raw_affiliation_strings', [])
                    raw_aff_str = '; '.join(raw_affs) if raw_affs else None

                    # Get institutions - create separate row for each institution
                    institutions = authorship.get('institutions', [])

                    if institutions:
                        # Author has institutions - create one row per institution
                        for inst in institutions:
                            inst_id = self.clean_openalex_id(inst.get('id'))
                            if inst_id:
                                authorship_batch.append({
                                    'work_id': work_id,
                                    'author_id': author_id,
                                    'author_position': author_position,
                                    'is_corresponding': is_corresponding,
                                    'raw_affiliation_string': raw_aff_str,
                                    'institution_id': inst_id
                                })
                    else:
                        # No institutions - create single row with NULL institution
                        authorship_batch.append({
                            'work_id': work_id,
                            'author_id': author_id,
                            'author_position': author_position,
                            'is_corresponding': is_corresponding,
                            'raw_affiliation_string': raw_aff_str,
                            'institution_id': None
                        })

                # Work topics
                topics = work.get('topics', [])
                for topic in topics:
                    topic_id = self.clean_openalex_id(topic.get('id'))
                    if topic_id:
                        work_topics_batch.append({
                            'work_id': work_id,
                            'topic_id': topic_id,
                            'score': topic.get('score'),
                            'is_primary_topic': topic.get('is_primary_topic', False)
                        })

                # Work concepts
                concepts = work.get('concepts', [])
                for concept in concepts:
                    concept_id = self.clean_openalex_id(concept.get('id'))
                    if concept_id:
                        work_concepts_batch.append({
                            'work_id': work_id,
                            'concept_id': concept_id,
                            'score': concept.get('score')
                        })

                # Work sources (from locations)
                locations = work.get('locations', [])
                for location in locations:
                    source = location.get('source', {}) or {}
                    source_id = self.clean_openalex_id(source.get('id'))
                    if source_id:
                        work_sources_batch.append({
                            'work_id': work_id,
                            'source_id': source_id
                        })

                # Work keywords
                keywords_list = work.get('keywords', [])
                for kw in keywords_list:
                    keyword = kw.get('keyword') or kw.get('display_name')
                    if keyword:
                        work_keywords_batch.append({
                            'work_id': work_id,
                            'keyword': keyword[:255]  # Limit length
                        })

                # Work funders (from grants)
                grants_list = work.get('grants', [])
                for grant in grants_list:
                    funder_id = self.clean_openalex_id(grant.get('funder'))
                    if funder_id:
                        work_funders_batch.append({
                            'work_id': work_id,
                            'funder_id': funder_id,
                            'award_id': grant.get('award_id')
                        })

                # Citations by year
                counts_by_year = work.get('counts_by_year', [])
                for count in counts_by_year:
                    year = count.get('year')
                    if year:
                        citations_by_year_batch.append({
                            'work_id': work_id,
                            'year': year,
                            'citation_count': count.get('cited_by_count')
                        })

                # Referenced works
                referenced = work.get('referenced_works', [])
                for ref_work in referenced:
                    ref_work_id = self.clean_openalex_id(ref_work)
                    if ref_work_id:
                        referenced_works_batch.append({
                            'work_id': work_id,
                            'referenced_work_id': ref_work_id
                        })

                # Related works
                related = work.get('related_works', [])
                for rel_work in related:
                    rel_work_id = self.clean_openalex_id(rel_work)
                    if rel_work_id:
                        related_works_batch.append({
                            'work_id': work_id,
                            'related_work_id': rel_work_id
                        })

                # APC (Article Processing Charges)
                apc_list = work.get('apc_list', {}) or {}
                apc_paid = work.get('apc_paid', {}) or {}

                # Use apc_paid if available, otherwise use apc_list
                if apc_paid:
                    apc_batch.append({
                        'work_id': work_id,
                        'value': apc_paid.get('value'),
                        'currency': apc_paid.get('currency'),
                        'value_usd': apc_paid.get('value_usd'),
                        'provenance': apc_paid.get('provenance')
                    })
                elif apc_list:
                    apc_batch.append({
                        'work_id': work_id,
                        'value': apc_list.get('value'),
                        'currency': apc_list.get('currency'),
                        'value_usd': apc_list.get('value_usd'),
                        'provenance': apc_list.get('provenance')
                    })

                self.stats['records_parsed'] += 1

                # Batch writes when threshold reached
                if len(works_batch) >= 10000:
                    self.write_with_copy('works', works_batch, self.works_columns)
                    works_batch = []

                if len(authorship_batch) >= 50000:
                    self.write_with_copy('authorship', authorship_batch, self.authorship_columns)
                    authorship_batch = []

                if len(work_topics_batch) >= 50000:
                    self.write_with_copy('work_topics', work_topics_batch, self.work_topics_columns)
                    work_topics_batch = []

                if len(work_concepts_batch) >= 50000:
                    self.write_with_copy('work_concepts', work_concepts_batch, self.work_concepts_columns)
                    work_concepts_batch = []

                if len(work_sources_batch) >= 50000:
                    self.write_with_copy('work_sources', work_sources_batch, self.work_sources_columns)
                    work_sources_batch = []

                if len(work_keywords_batch) >= 50000:
                    self.write_with_copy('work_keywords', work_keywords_batch, self.work_keywords_columns)
                    work_keywords_batch = []

                if len(work_funders_batch) >= 50000:
                    self.write_with_copy('work_funders', work_funders_batch, self.work_funders_columns)
                    work_funders_batch = []

                if len(citations_by_year_batch) >= 50000:
                    self.write_with_copy('citations_by_year', citations_by_year_batch, self.citations_by_year_columns)
                    citations_by_year_batch = []

                if len(referenced_works_batch) >= 50000:
                    self.write_with_copy('referenced_works', referenced_works_batch, self.referenced_works_columns)
                    referenced_works_batch = []

                if len(related_works_batch) >= 50000:
                    self.write_with_copy('related_works', related_works_batch, self.related_works_columns)
                    related_works_batch = []

                if len(apc_batch) >= 50000:
                    self.write_with_copy('apc', apc_batch, self.apc_columns)
                    apc_batch = []

            # Write remaining records
            if works_batch:
                self.write_with_copy('works', works_batch, self.works_columns)
            if authorship_batch:
                self.write_with_copy('authorship', authorship_batch, self.authorship_columns)
            if work_topics_batch:
                self.write_with_copy('work_topics', work_topics_batch, self.work_topics_columns)
            if work_concepts_batch:
                self.write_with_copy('work_concepts', work_concepts_batch, self.work_concepts_columns)
            if work_sources_batch:
                self.write_with_copy('work_sources', work_sources_batch, self.work_sources_columns)
            if work_keywords_batch:
                self.write_with_copy('work_keywords', work_keywords_batch, self.work_keywords_columns)
            if work_funders_batch:
                self.write_with_copy('work_funders', work_funders_batch, self.work_funders_columns)
            if citations_by_year_batch:
                self.write_with_copy('citations_by_year', citations_by_year_batch, self.citations_by_year_columns)
            if referenced_works_batch:
                self.write_with_copy('referenced_works', referenced_works_batch, self.referenced_works_columns)
            if related_works_batch:
                self.write_with_copy('related_works', related_works_batch, self.related_works_columns)
            if apc_batch:
                self.write_with_copy('apc', apc_batch, self.apc_columns)

        finally:
            self.stats['end_time'] = time.time()
            self.close_db()
            self.print_stats()

        return self.stats


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Parse OpenAlex works with COPY')
    parser.add_argument('--input-file', required=True, help='Path to works .gz file')
    parser.add_argument('--limit', type=int, help='Limit number of lines (testing)')
    args = parser.parse_args()

    try:
        works_parser = WorksParser(args.input_file, line_limit=args.limit)
        stats = works_parser.parse()
        sys.exit(0 if stats['errors'] == 0 else 1)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

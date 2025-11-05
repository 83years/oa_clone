#!/usr/bin/env python3
"""
Parse OpenAlex Sources - Version 2 with COPY support
Populates: sources, source_publishers
"""
import json
import time
import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from base_parser import BaseParser


class SourcesParser(BaseParser):
    """Parser for sources and source-publisher relationships"""

    def __init__(self, input_file, line_limit=None):
        super().__init__('sources', input_file, line_limit)

        self.sources_columns = [
            'source_id', 'display_name', 'issn_l', 'host', 'host_organization',
            'host_organization_lineage', 'type', 'issn', 'host_organization_name',
            'is_oa', 'is_in_doaj', 'works_count', 'cited_by_count', 'updated_date'
        ]

        self.source_publishers_columns = ['source_id', 'publisher_id']

    def parse(self):
        """Main parsing logic"""
        self.stats['start_time'] = time.time()
        self.connect_db()

        sources_batch = []
        source_publishers_batch = []
        unique_ids = set()

        try:
            for source in self.read_gz_stream():
                source_id = self.clean_openalex_id(source.get('id'))
                if not source_id or source_id in unique_ids:
                    continue

                unique_ids.add(source_id)

                # Extract host organization (can be string or dict)
                host_org = source.get('host_organization')
                host_org_id = None
                host_org_name = None
                host_org_lineage = None

                if isinstance(host_org, dict):
                    host_org_id = self.clean_openalex_id(host_org.get('id'))
                    host_org_name = host_org.get('display_name')
                    lineage = host_org.get('lineage', [])
                    if lineage:
                        host_org_lineage = json.dumps([self.clean_openalex_id(l) for l in lineage])
                elif isinstance(host_org, str):
                    host_org_id = self.clean_openalex_id(host_org)

                # Convert ISSN list to JSON
                issn_list = source.get('issn')
                issn_str = json.dumps(issn_list) if issn_list else None

                # Main source record
                sources_batch.append({
                    'source_id': source_id,
                    'display_name': source.get('display_name'),
                    'issn_l': source.get('issn_l'),
                    'host': None,  # Legacy field
                    'host_organization': host_org_id,
                    'host_organization_lineage': host_org_lineage,
                    'type': source.get('type'),
                    'issn': issn_str,
                    'host_organization_name': host_org_name,
                    'is_oa': str(source.get('is_oa')) if source.get('is_oa') is not None else None,
                    'is_in_doaj': str(source.get('is_in_doaj')) if source.get('is_in_doaj') is not None else None,
                    'works_count': source.get('works_count'),
                    'cited_by_count': source.get('cited_by_count'),
                    'updated_date': source.get('updated_date')
                })

                # Extract publisher relationships
                # Check multiple possible locations for publisher info
                publisher_id = None

                # Method 1: Direct publisher field
                if source.get('publisher'):
                    publisher_id = self.clean_openalex_id(source.get('publisher'))

                # Method 2: Host organization as publisher
                elif source.get('host_organization_name'):
                    # Sometimes the host org is the publisher
                    societies = source.get('societies', [])
                    if societies:
                        for society in societies:
                            soc_id = self.clean_openalex_id(society.get('id'))
                            if soc_id:
                                source_publishers_batch.append({
                                    'source_id': source_id,
                                    'publisher_id': soc_id
                                })

                if publisher_id:
                    source_publishers_batch.append({
                        'source_id': source_id,
                        'publisher_id': publisher_id
                    })

                self.stats['records_parsed'] += 1

                # Batch writes
                if len(sources_batch) >= 50000:
                    self.write_with_copy('sources', sources_batch, self.sources_columns)
                    sources_batch = []

                if len(source_publishers_batch) >= 50000:
                    self.write_with_copy('source_publishers', source_publishers_batch, self.source_publishers_columns)
                    source_publishers_batch = []

            # Write remaining
            if sources_batch:
                self.write_with_copy('sources', sources_batch, self.sources_columns)
            if source_publishers_batch:
                self.write_with_copy('source_publishers', source_publishers_batch, self.source_publishers_columns)

        finally:
            self.stats['end_time'] = time.time()
            self.close_db()
            self.print_stats()

        return self.stats


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Parse OpenAlex sources with COPY')
    parser.add_argument('--input-file', required=True, help='Path to sources .gz file')
    parser.add_argument('--limit', type=int, help='Limit number of lines (testing)')
    args = parser.parse_args()

    try:
        sources_parser = SourcesParser(args.input_file, line_limit=args.limit)
        stats = sources_parser.parse()
        sys.exit(0 if stats['errors'] == 0 else 1)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

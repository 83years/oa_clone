#!/usr/bin/env python3
"""
Parse OpenAlex Institutions - Version 2 with COPY support
Populates: institutions, institution_geo, institution_hierarchy
"""
import json
import time
import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from base_parser import BaseParser


class InstitutionsParser(BaseParser):
    """Parser for institutions, geo data, and hierarchy"""

    def __init__(self, input_file, line_limit=None):
        super().__init__('institutions', input_file, line_limit)

        self.institutions_columns = [
            'institution_id', 'display_name', 'display_name_acronyms', 'display_name_alternatives',
            'ror', 'ror_id', 'country_code', 'type', 'lineage', 'homepage_url',
            'image_url', 'image_thumbnail_url', 'works_count', 'cited_by_count',
            'created_date', 'updated_date', 'openalex', 'grid', 'wikipedia', 'wikidata',
            'mag', 'summary_stats_2yr_mean_citedness', 'summary_stats_h_index',
            'summary_stats_i10_index', 'associated_institutions'
        ]

        self.institution_geo_columns = [
            'institution_id', 'city', 'geonames_city_id', 'region',
            'country_code', 'country', 'latitude', 'longitude'
        ]

        self.institution_hierarchy_columns = [
            'parent_institution_id', 'child_institution_id', 'hierarchy_level', 'relationship_type'
        ]

    def parse(self):
        """Main parsing logic"""
        self.stats['start_time'] = time.time()
        self.connect_db()

        institutions_batch = []
        institution_geo_batch = []
        institution_hierarchy_batch = []
        unique_ids = set()

        try:
            for inst in self.read_gz_stream():
                inst_id = self.clean_openalex_id(inst.get('id'))
                if not inst_id or inst_id in unique_ids:
                    continue

                unique_ids.add(inst_id)

                # Extract lineage for hierarchy
                lineage = inst.get('lineage', [])
                lineage_clean = [self.clean_openalex_id(l) for l in lineage if l]
                lineage_str = json.dumps(lineage_clean) if lineage_clean else None

                # Build hierarchy relationships from lineage
                if lineage_clean and len(lineage_clean) > 1:
                    for i in range(len(lineage_clean) - 1):
                        parent_id = lineage_clean[i]
                        child_id = lineage_clean[i + 1]

                        # Avoid self-references
                        if parent_id and child_id and parent_id != child_id:
                            institution_hierarchy_batch.append({
                                'parent_institution_id': parent_id,
                                'child_institution_id': child_id,
                                'hierarchy_level': i + 1,
                                'relationship_type': 'direct_parent'
                            })

                # Extract IDs from ids object
                ids = inst.get('ids', {}) or {}

                # Extract summary stats
                summary_stats = inst.get('summary_stats', {}) or {}

                # Extract associated institutions
                associated = inst.get('associated_institutions', [])
                associated_str = None
                if associated:
                    associated_ids = [self.clean_openalex_id(a.get('id')) for a in associated if a.get('id')]
                    associated_str = json.dumps(associated_ids) if associated_ids else None

                # Convert display name arrays to JSON
                acronyms = inst.get('display_name_acronyms')
                acronyms_str = json.dumps(acronyms) if acronyms else None

                alternatives = inst.get('display_name_alternatives')
                alternatives_str = json.dumps(alternatives) if alternatives else None

                # Extract ROR
                ror = inst.get('ror', '')
                if ror:
                    ror = ror.replace('https://ror.org/', '')

                ror_id = ids.get('ror', '')
                if ror_id:
                    ror_id = ror_id.replace('https://ror.org/', '')

                # Extract type
                inst_type = inst.get('type', '')
                if inst_type:
                    inst_type = inst_type.replace('https://openalex.org/institution-types/', '')

                # Main institution record
                institutions_batch.append({
                    'institution_id': inst_id,
                    'display_name': inst.get('display_name'),
                    'display_name_acronyms': acronyms_str,
                    'display_name_alternatives': alternatives_str,
                    'ror': ror if ror else None,
                    'ror_id': ror_id if ror_id else None,
                    'country_code': inst.get('country_code'),
                    'type': inst_type if inst_type else None,
                    'lineage': lineage_str,
                    'homepage_url': inst.get('homepage_url'),
                    'image_url': inst.get('image_url'),
                    'image_thumbnail_url': inst.get('image_thumbnail_url'),
                    'works_count': inst.get('works_count'),
                    'cited_by_count': inst.get('cited_by_count'),
                    'created_date': inst.get('created_date'),
                    'updated_date': inst.get('updated_date'),
                    'openalex': ids.get('openalex'),
                    'grid': ids.get('grid', '').replace('https://grid.ac/institutes/', '') if ids.get('grid') else None,
                    'wikipedia': ids.get('wikipedia'),
                    'wikidata': ids.get('wikidata', '').replace('https://www.wikidata.org/wiki/', '') if ids.get('wikidata') else None,
                    'mag': ids.get('mag'),
                    'summary_stats_2yr_mean_citedness': summary_stats.get('2yr_mean_citedness'),
                    'summary_stats_h_index': summary_stats.get('h_index'),
                    'summary_stats_i10_index': summary_stats.get('i10_index'),
                    'associated_institutions': associated_str
                })

                # Extract geo data
                geo = inst.get('geo', {}) or {}
                if geo:
                    institution_geo_batch.append({
                        'institution_id': inst_id,
                        'city': geo.get('city'),
                        'geonames_city_id': geo.get('geonames_city_id'),
                        'region': geo.get('region'),
                        'country_code': geo.get('country_code'),
                        'country': geo.get('country'),
                        'latitude': geo.get('latitude'),
                        'longitude': geo.get('longitude')
                    })

                self.stats['records_parsed'] += 1

                # Batch writes
                if len(institutions_batch) >= 50000:
                    self.write_with_copy('institutions', institutions_batch, self.institutions_columns)
                    institutions_batch = []

                if len(institution_geo_batch) >= 50000:
                    self.write_with_copy('institution_geo', institution_geo_batch, self.institution_geo_columns)
                    institution_geo_batch = []

                if len(institution_hierarchy_batch) >= 50000:
                    self.write_with_copy('institution_hierarchy', institution_hierarchy_batch, self.institution_hierarchy_columns)
                    institution_hierarchy_batch = []

            # Write remaining
            if institutions_batch:
                self.write_with_copy('institutions', institutions_batch, self.institutions_columns)
            if institution_geo_batch:
                self.write_with_copy('institution_geo', institution_geo_batch, self.institution_geo_columns)
            if institution_hierarchy_batch:
                self.write_with_copy('institution_hierarchy', institution_hierarchy_batch, self.institution_hierarchy_columns)

        finally:
            self.stats['end_time'] = time.time()
            self.close_db()
            self.print_stats()

        return self.stats


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Parse OpenAlex institutions with COPY')
    parser.add_argument('--input-file', required=True, help='Path to institutions .gz file')
    parser.add_argument('--limit', type=int, help='Limit number of lines (testing)')
    args = parser.parse_args()

    try:
        institutions_parser = InstitutionsParser(args.input_file, line_limit=args.limit)
        stats = institutions_parser.parse()
        sys.exit(0 if stats['errors'] == 0 else 1)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

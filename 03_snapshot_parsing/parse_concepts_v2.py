#!/usr/bin/env python3
"""
Parse OpenAlex Concepts - Version 2 with COPY support
Populates: concepts
"""
import time
import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from base_parser import BaseParser


class ConceptsParser(BaseParser):
    """Parser for concepts (simple, single table)"""

    def __init__(self, input_file, line_limit=None):
        super().__init__('concepts', input_file, line_limit)
        self.columns = [
            'concept_id', 'display_name', 'level', 'score', 'wikidata',
            'description', 'works_count', 'cited_by_count', 'updated_date'
        ]

    def parse(self):
        """Main parsing logic"""
        self.stats['start_time'] = time.time()
        self.connect_db()

        batch = []
        unique_ids = set()

        try:
            for concept in self.read_gz_stream():
                concept_id = self.clean_openalex_id(concept.get('id'))
                if not concept_id or concept_id in unique_ids:
                    continue

                unique_ids.add(concept_id)

                # Clean wikidata ID
                wikidata = concept.get('wikidata', '')
                if wikidata:
                    wikidata = wikidata.replace('https://www.wikidata.org/entity/', '')

                batch.append({
                    'concept_id': concept_id,
                    'display_name': concept.get('display_name'),
                    'level': concept.get('level'),
                    'score': concept.get('score'),
                    'wikidata': wikidata if wikidata else None,
                    'description': concept.get('description'),
                    'works_count': concept.get('works_count'),
                    'cited_by_count': concept.get('cited_by_count'),
                    'updated_date': concept.get('updated_date')
                })

                self.stats['records_parsed'] += 1

                # Batch write
                if len(batch) >= 50000:
                    self.write_with_copy('concepts', batch, self.columns)
                    batch = []

            # Write remaining
            if batch:
                self.write_with_copy('concepts', batch, self.columns)

        finally:
            self.stats['end_time'] = time.time()
            self.close_db()
            self.print_stats()

        return self.stats


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Parse OpenAlex concepts with COPY')
    parser.add_argument('--input-file', required=True, help='Path to concepts .gz file')
    parser.add_argument('--limit', type=int, help='Limit number of lines (testing)')
    args = parser.parse_args()

    try:
        concepts_parser = ConceptsParser(args.input_file, line_limit=args.limit)
        stats = concepts_parser.parse()
        sys.exit(0 if stats['errors'] == 0 else 1)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

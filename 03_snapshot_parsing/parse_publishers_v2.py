#!/usr/bin/env python3
"""
Parse OpenAlex Publishers - Version 2 with COPY support
Populates: publishers
"""
import time
import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from base_parser import BaseParser


class PublishersParser(BaseParser):
    """Parser for publishers (simple, single table)"""

    def __init__(self, input_file, line_limit=None):
        super().__init__('publishers', input_file, line_limit)
        self.columns = [
            'publisher_id', 'display_name', 'country_code', 'hierarchy_level'
        ]

    def parse(self):
        """Main parsing logic"""
        self.stats['start_time'] = time.time()
        self.connect_db()

        batch = []
        unique_ids = set()

        try:
            for publisher in self.read_gz_stream():
                publisher_id = self.clean_openalex_id(publisher.get('id'))
                if not publisher_id or publisher_id in unique_ids:
                    continue

                unique_ids.add(publisher_id)

                # Handle country_codes array - take first element
                country_codes = publisher.get('country_codes', [])
                country_code = country_codes[0] if country_codes else None

                # Handle hierarchy_level (might be integer or string)
                hierarchy = publisher.get('hierarchy_level')

                batch.append({
                    'publisher_id': publisher_id,
                    'display_name': publisher.get('display_name'),
                    'country_code': country_code,
                    'hierarchy_level': str(hierarchy) if hierarchy is not None else None
                })

                self.stats['records_parsed'] += 1

                # Batch write
                if len(batch) >= 50000:
                    self.write_with_copy('publishers', batch, self.columns)
                    batch = []

            # Write remaining
            if batch:
                self.write_with_copy('publishers', batch, self.columns)

        finally:
            self.stats['end_time'] = time.time()
            self.close_db()
            self.print_stats()

        return self.stats


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Parse OpenAlex publishers with COPY')
    parser.add_argument('--input-file', required=True, help='Path to publishers .gz file')
    parser.add_argument('--limit', type=int, help='Limit number of lines (testing)')
    args = parser.parse_args()

    try:
        publishers_parser = PublishersParser(args.input_file, line_limit=args.limit)
        stats = publishers_parser.parse()
        sys.exit(0 if stats['errors'] == 0 else 1)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

#!/usr/bin/env python3
"""
Parse OpenAlex Funders - Version 2 with COPY support
Populates: funders
"""
import time
import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from base_parser import BaseParser


class FundersParser(BaseParser):
    """Parser for funders (simple, single table)"""

    def __init__(self, input_file, line_limit=None):
        super().__init__('funders', input_file, line_limit)
        self.columns = [
            'funder_id', 'display_name', 'country_code', 'description', 'homepage_url'
        ]

    def parse(self):
        """Main parsing logic"""
        self.stats['start_time'] = time.time()
        self.connect_db()

        batch = []
        unique_ids = set()

        try:
            for funder in self.read_gz_stream():
                funder_id = self.clean_openalex_id(funder.get('id'))
                if not funder_id or funder_id in unique_ids:
                    continue

                unique_ids.add(funder_id)

                batch.append({
                    'funder_id': funder_id,
                    'display_name': funder.get('display_name'),
                    'country_code': funder.get('country_code'),
                    'description': funder.get('description'),
                    'homepage_url': funder.get('homepage_url')
                })

                self.stats['records_parsed'] += 1

                # Batch write
                if len(batch) >= 50000:
                    self.write_with_copy('funders', batch, self.columns)
                    batch = []

            # Write remaining
            if batch:
                self.write_with_copy('funders', batch, self.columns)

        finally:
            self.stats['end_time'] = time.time()
            self.close_db()
            self.print_stats()

        return self.stats


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Parse OpenAlex funders with COPY')
    parser.add_argument('--input-file', required=True, help='Path to funders .gz file')
    parser.add_argument('--limit', type=int, help='Limit number of lines (testing)')
    args = parser.parse_args()

    try:
        funders_parser = FundersParser(args.input_file, line_limit=args.limit)
        stats = funders_parser.parse()
        sys.exit(0 if stats['errors'] == 0 else 1)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

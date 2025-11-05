#!/usr/bin/env python3
"""
Parse OpenAlex Topics - Version 2 with COPY support
Populates: topics, topic_hierarchy
"""
import json
import time
import argparse
import sys
from pathlib import Path

# Add parent directory to path
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

from base_parser import BaseParser


class TopicsParser(BaseParser):
    """Parser for topics and topic hierarchy"""

    def __init__(self, input_file, line_limit=None):
        super().__init__('topics', input_file, line_limit)
        self.topics_columns = [
            'topic_id', 'display_name', 'score', 'subfield_id', 'subfield_display_name',
            'field_id', 'field_display_name', 'domain_id', 'domain_display_name',
            'description', 'keywords', 'works_count', 'cited_by_count', 'updated_date'
        ]
        self.hierarchy_columns = [
            'parent_topic_id', 'child_topic_id', 'hierarchy_level'
        ]

    def parse(self):
        """Main parsing logic"""
        self.stats['start_time'] = time.time()
        self.connect_db()

        topics_batch = []
        hierarchy_batch = []
        unique_ids = set()

        try:
            for topic in self.read_gz_stream():
                # Extract and clean topic ID
                topic_id = self.clean_openalex_id(topic.get('id'))
                if not topic_id or topic_id in unique_ids:
                    continue

                unique_ids.add(topic_id)

                # Extract hierarchy IDs
                domain = topic.get('domain', {}) or {}
                field = topic.get('field', {}) or {}
                subfield = topic.get('subfield', {}) or {}

                domain_id = self.clean_openalex_id(domain.get('id'))
                field_id = self.clean_openalex_id(field.get('id'))
                subfield_id = self.clean_openalex_id(subfield.get('id'))

                # Keywords array to string
                keywords = topic.get('keywords')
                keywords_str = ', '.join(keywords) if keywords else None

                # Main topic record
                topics_batch.append({
                    'topic_id': topic_id,
                    'display_name': topic.get('display_name'),
                    'score': topic.get('score'),
                    'subfield_id': subfield_id,
                    'subfield_display_name': subfield.get('display_name'),
                    'field_id': field_id,
                    'field_display_name': field.get('display_name'),
                    'domain_id': domain_id,
                    'domain_display_name': domain.get('display_name'),
                    'description': topic.get('description'),
                    'keywords': keywords_str,
                    'works_count': topic.get('works_count'),
                    'cited_by_count': topic.get('cited_by_count'),
                    'updated_date': topic.get('updated_date')
                })

                # Build hierarchy: domain -> field -> subfield -> topic
                # Domain is top level (no parent)
                # Field -> Domain
                if field_id and domain_id and field_id != domain_id:
                    hierarchy_batch.append({
                        'parent_topic_id': domain_id,
                        'child_topic_id': field_id,
                        'hierarchy_level': 1
                    })

                # Subfield -> Field
                if subfield_id and field_id and subfield_id != field_id:
                    hierarchy_batch.append({
                        'parent_topic_id': field_id,
                        'child_topic_id': subfield_id,
                        'hierarchy_level': 2
                    })

                # Topic -> Subfield
                if topic_id and subfield_id and topic_id != subfield_id:
                    hierarchy_batch.append({
                        'parent_topic_id': subfield_id,
                        'child_topic_id': topic_id,
                        'hierarchy_level': 3
                    })

                self.stats['records_parsed'] += 1

                # Batch write when threshold reached
                if len(topics_batch) >= self.stats.get('batch_size', 50000):
                    self.write_with_copy('topics', topics_batch, self.topics_columns)
                    topics_batch = []

                if len(hierarchy_batch) >= self.stats.get('batch_size', 50000):
                    self.write_with_copy('topic_hierarchy', hierarchy_batch, self.hierarchy_columns)
                    hierarchy_batch = []

            # Write remaining records
            if topics_batch:
                self.write_with_copy('topics', topics_batch, self.topics_columns)

            if hierarchy_batch:
                self.write_with_copy('topic_hierarchy', hierarchy_batch, self.hierarchy_columns)

        finally:
            self.stats['end_time'] = time.time()
            self.close_db()
            self.print_stats()

        return self.stats


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Parse OpenAlex topics with COPY')
    parser.add_argument('--input-file', required=True, help='Path to topics .gz file')
    parser.add_argument('--limit', type=int, help='Limit number of lines to process (for testing)')
    args = parser.parse_args()

    try:
        topics_parser = TopicsParser(args.input_file, line_limit=args.limit)
        stats = topics_parser.parse()
        sys.exit(0 if stats['errors'] == 0 else 1)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

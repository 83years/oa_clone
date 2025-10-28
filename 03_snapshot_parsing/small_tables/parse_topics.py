#!/usr/bin/env python3
"""Parse OpenAlex Topics"""
import json
import gzip
import psycopg2
from psycopg2.extras import execute_values
import pandas as pd
import argparse
import sys
from pathlib import Path

# Add parent directory to path for config imports
SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(PARENT_DIR))

from config import DB_CONFIG, BATCH_SIZE, PROGRESS_INTERVAL

def parse_topics(input_file):
    """Parse topics from gz file"""
    print(f"Reading {input_file}...")

    topics_main = []
    topic_hierarchy = []
    unique_topics = set()
    stats = {
        'topics_processed': 0,
        'hierarchy_relationships': 0,
        'topics_with_description': 0,
        'topics_with_keywords': 0
    }
    
    with gzip.open(input_file, 'rt', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            if i % PROGRESS_INTERVAL == 0:
                print(f"  Processed {i:,} lines...")
            
            line = line.strip()
            if not line:
                continue
            
            try:
                topic = json.loads(line)
            except:
                continue
            
            topic_id = topic.get('id', '').replace('https://openalex.org/', '')
            if not topic_id or topic_id in unique_topics:
                continue

            # Extract domain, field, subfield IDs and names
            domain = topic.get('domain', {})
            domain_id = domain.get('id', '').replace('https://openalex.org/', '') if domain else ''
            domain_display_name = domain.get('display_name', '') if domain else ''

            field = topic.get('field', {})
            field_id = field.get('id', '').replace('https://openalex.org/', '') if field else ''
            field_display_name = field.get('display_name', '') if field else ''

            subfield = topic.get('subfield', {})
            subfield_id = subfield.get('id', '').replace('https://openalex.org/', '') if subfield else ''
            subfield_display_name = subfield.get('display_name', '') if subfield else ''

            # Extract keywords (convert list to comma-separated string)
            keywords_list = topic.get('keywords', [])
            keywords_str = ', '.join(keywords_list) if isinstance(keywords_list, list) else ''

            # Main topic record
            topics_main.append({
                'topic_id': topic_id,
                'display_name': topic.get('display_name', ''),
                'score': 0,  # Not in source data
                'subfield_id': subfield_id,
                'subfield_display_name': subfield_display_name,
                'field_id': field_id,
                'field_display_name': field_display_name,
                'domain_id': domain_id,
                'domain_display_name': domain_display_name,
                'description': topic.get('description', ''),
                'keywords': keywords_str,
                'works_count': topic.get('works_count', 0),
                'cited_by_count': topic.get('cited_by_count', 0),
                'updated_date': topic.get('updated_date', None)
            })
            unique_topics.add(topic_id)

            # Track statistics
            stats['topics_processed'] += 1
            if topic.get('description'):
                stats['topics_with_description'] += 1
            if keywords_list:
                stats['topics_with_keywords'] += 1

            # Build hierarchy relationships
            # Relationship: subfield → topic
            if subfield_id and topic_id:
                topic_hierarchy.append({
                    'parent_topic_id': subfield_id,
                    'child_topic_id': topic_id,
                    'hierarchy_level': 1
                })
                stats['hierarchy_relationships'] += 1

            # Relationship: field → subfield
            if field_id and subfield_id:
                topic_hierarchy.append({
                    'parent_topic_id': field_id,
                    'child_topic_id': subfield_id,
                    'hierarchy_level': 2
                })
                stats['hierarchy_relationships'] += 1

            # Relationship: domain → field
            if domain_id and field_id:
                topic_hierarchy.append({
                    'parent_topic_id': domain_id,
                    'child_topic_id': field_id,
                    'hierarchy_level': 3
                })
                stats['hierarchy_relationships'] += 1

    # Print summary statistics
    print(f"\n📊 Parsing Summary:")
    print(f"  ✅ Topics processed: {stats['topics_processed']:,}")
    print(f"  ✅ Topics with descriptions: {stats['topics_with_description']:,}")
    print(f"  ✅ Topics with keywords: {stats['topics_with_keywords']:,}")
    print(f"  ✅ Hierarchy relationships: {stats['hierarchy_relationships']:,}")

    return topics_main, topic_hierarchy

def write_to_db(topics_main, topic_hierarchy):
    """Write to database"""
    print("\nConnecting to database...")
    conn = psycopg2.connect(**DB_CONFIG)
    
    # Disable FK constraints
    cursor = conn.cursor()
    cursor.execute("SET session_replication_role = replica;")
    conn.commit()
    cursor.close()
    
    # Write topics
    if topics_main:
        print(f"Writing {len(topics_main):,} topics...")
        df = pd.DataFrame(topics_main).where(pd.notnull(pd.DataFrame(topics_main)), None)
        data = [tuple(row) for row in df.values]
        cursor = conn.cursor()
        sql = f"INSERT INTO topics ({','.join(df.columns)}) VALUES %s ON CONFLICT DO NOTHING"
        execute_values(cursor, sql, data, page_size=BATCH_SIZE)
        conn.commit()
        cursor.close()
    
    # Write hierarchy
    if topic_hierarchy:
        print(f"Writing {len(topic_hierarchy):,} hierarchy relationships...")
        df = pd.DataFrame(topic_hierarchy).where(pd.notnull(pd.DataFrame(topic_hierarchy)), None)
        data = [tuple(row) for row in df.values]
        cursor = conn.cursor()
        sql = f"INSERT INTO topic_hierarchy ({','.join(df.columns)}) VALUES %s ON CONFLICT DO NOTHING"
        execute_values(cursor, sql, data, page_size=BATCH_SIZE)
        conn.commit()
        cursor.close()
    
    # Re-enable FK constraints
    cursor = conn.cursor()
    cursor.execute("SET session_replication_role = default;")
    conn.commit()
    cursor.close()
    conn.close()
    
    print("✅ Complete")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-file', required=True)
    parser.add_argument('--mode', choices=['clean', 'update'], default='clean',
                       help="Processing mode (clean or update)")
    args = parser.parse_args()
    
    try:
        topics_main, topic_hierarchy = parse_topics(args.input_file)
        write_to_db(topics_main, topic_hierarchy)
        sys.exit(0)
    except Exception as e:
        print(f"âŒ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
#!/usr/bin/env python3
"""Parse OpenAlex Topics"""
import json
import gzip
import psycopg2
from psycopg2.extras import execute_values
import pandas as pd
import argparse
import sys
from config import DB_CONFIG, BATCH_SIZE, PROGRESS_INTERVAL

def parse_topics(input_file):
    """Parse topics from gz file"""
    print(f"Reading {input_file}...")
    
    topics_main = []
    topic_hierarchy = []
    unique_topics = set()
    
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
            
            # Main topic
            topics_main.append({
                'topic_id': topic_id,
                'display_name': topic.get('display_name', ''),
                'score': topic.get('score', 0),
                'subfield_id': '',
                'subfield_display_name': '',
                'field_id': '',
                'field_display_name': '',
                'domain_id': '',
                'domain_display_name': ''
            })
            unique_topics.add(topic_id)
            
            # Extract hierarchy
            subfield = topic.get('subfield', {})
            if subfield:
                subfield_id = subfield.get('id', '').replace('https://openalex.org/', '')
                if subfield_id and subfield_id not in unique_topics:
                    topics_main.append({
                        'topic_id': subfield_id,
                        'display_name': subfield.get('display_name', ''),
                        'score': 0,
                        'subfield_id': '',
                        'subfield_display_name': '',
                        'field_id': '',
                        'field_display_name': '',
                        'domain_id': '',
                        'domain_display_name': ''
                    })
                    unique_topics.add(subfield_id)
                
                if topic_id and subfield_id:
                    topic_hierarchy.append({
                        'parent_topic_id': subfield_id,
                        'child_topic_id': topic_id,
                        'hierarchy_level': 1
                    })
    
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
    
    print("âœ… Complete")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-file', required=True)
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
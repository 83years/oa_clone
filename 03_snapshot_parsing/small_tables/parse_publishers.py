#!/usr/bin/env python3
"""Parse OpenAlex Publishers"""
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

def parse_publishers(input_file):
    """Parse publishers from gz file"""
    print(f"Reading {input_file}...")
    
    publishers = []
    unique_ids = set()
    
    with gzip.open(input_file, 'rt', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            if i % PROGRESS_INTERVAL == 0:
                print(f"  Processed {i:,} lines...")
            
            line = line.strip()
            if not line:
                continue
            
            try:
                pub = json.loads(line)
            except:
                continue
            
            pub_id = pub.get('id', '').replace('https://openalex.org/', '')
            if not pub_id or pub_id in unique_ids:
                continue
            
            # Extract country_codes (it's an array in source data)
            country_codes = pub.get('country_codes', [])
            country_code = country_codes[0] if country_codes else ''

            publishers.append({
                'publisher_id': pub_id,
                'display_name': pub.get('display_name', ''),
                'country_code': country_code,
                'hierarchy_level': pub.get('hierarchy_level', None)
            })
            unique_ids.add(pub_id)
    
    return publishers

def write_to_db(publishers):
    """Write to database"""
    print("\nConnecting to database...")
    conn = psycopg2.connect(**DB_CONFIG)
    
    cursor = conn.cursor()
    cursor.execute("SET session_replication_role = replica;")
    conn.commit()
    cursor.close()
    
    if publishers:
        print(f"Writing {len(publishers):,} publishers...")
        df = pd.DataFrame(publishers).where(pd.notnull(pd.DataFrame(publishers)), None)
        data = [tuple(row) for row in df.values]
        cursor = conn.cursor()
        sql = f"INSERT INTO publishers ({','.join(df.columns)}) VALUES %s ON CONFLICT DO NOTHING"
        execute_values(cursor, sql, data, page_size=BATCH_SIZE)
        conn.commit()
        cursor.close()
    
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
                       help='Processing mode (clean or update)')
    args = parser.parse_args()
    
    try:
        publishers = parse_publishers(args.input_file)
        write_to_db(publishers)
        sys.exit(0)
    except Exception as e:
        print(f"âŒ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
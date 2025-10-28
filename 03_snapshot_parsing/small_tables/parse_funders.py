#!/usr/bin/env python3
"""Parse OpenAlex Funders"""
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

def parse_funders(input_file):
    """Parse funders from gz file"""
    print(f"Reading {input_file}...")
    
    funders = []
    unique_ids = set()
    
    with gzip.open(input_file, 'rt', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            if i % PROGRESS_INTERVAL == 0:
                print(f"  Processed {i:,} lines...")
            
            line = line.strip()
            if not line:
                continue
            
            try:
                funder = json.loads(line)
            except:
                continue
            
            funder_id = funder.get('id', '').replace('https://openalex.org/', '')
            if not funder_id or funder_id in unique_ids:
                continue
            
            funders.append({
                'funder_id': funder_id,
                'display_name': funder.get('display_name', ''),
                'country_code': funder.get('country_code', ''),
                'description': funder.get('description', ''),
                'homepage_url': funder.get('homepage_url', '')
            })
            unique_ids.add(funder_id)
    
    return funders

def write_to_db(funders):
    """Write to database"""
    print("\nConnecting to database...")
    conn = psycopg2.connect(**DB_CONFIG)
    
    cursor = conn.cursor()
    cursor.execute("SET session_replication_role = replica;")
    conn.commit()
    cursor.close()
    
    if funders:
        print(f"Writing {len(funders):,} funders...")
        df = pd.DataFrame(funders).where(pd.notnull(pd.DataFrame(funders)), None)
        data = [tuple(row) for row in df.values]
        cursor = conn.cursor()
        sql = f"INSERT INTO funders ({','.join(df.columns)}) VALUES %s ON CONFLICT DO NOTHING"
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
        funders = parse_funders(args.input_file)
        write_to_db(funders)
        sys.exit(0)
    except Exception as e:
        print(f"âŒ Error: {e}")
        sys.exit(1)
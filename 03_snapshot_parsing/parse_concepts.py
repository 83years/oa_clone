#!/usr/bin/env python3
"""Parse OpenAlex Concepts"""
import json
import gzip
import psycopg2
from psycopg2.extras import execute_values
import pandas as pd
import argparse
import sys
from config import DB_CONFIG, BATCH_SIZE, PROGRESS_INTERVAL

def parse_concepts(input_file):
    """Parse concepts from gz file"""
    print(f"Reading {input_file}...")
    
    concepts = []
    unique_ids = set()
    
    with gzip.open(input_file, 'rt', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            if i % PROGRESS_INTERVAL == 0:
                print(f"  Processed {i:,} lines...")
            
            line = line.strip()
            if not line:
                continue
            
            try:
                concept = json.loads(line)
            except:
                continue
            
            concept_id = concept.get('id', '').replace('https://openalex.org/', '')
            if not concept_id or concept_id in unique_ids:
                continue
            
            concepts.append({
                'concept_id': concept_id,
                'display_name': concept.get('display_name', ''),
                'level': concept.get('level', 0),
                'score': concept.get('score', 0.0),
                'wikidata': concept.get('wikidata', '').replace('https://www.wikidata.org/entity/', '')
            })
            unique_ids.add(concept_id)
    
    return concepts

def write_to_db(concepts):
    """Write to database"""
    print("\nConnecting to database...")
    conn = psycopg2.connect(**DB_CONFIG)
    
    cursor = conn.cursor()
    cursor.execute("SET session_replication_role = replica;")
    conn.commit()
    cursor.close()
    
    if concepts:
        print(f"Writing {len(concepts):,} concepts...")
        df = pd.DataFrame(concepts).where(pd.notnull(pd.DataFrame(concepts)), None)
        data = [tuple(row) for row in df.values]
        cursor = conn.cursor()
        sql = f"INSERT INTO concepts ({','.join(df.columns)}) VALUES %s ON CONFLICT DO NOTHING"
        execute_values(cursor, sql, data, page_size=BATCH_SIZE)
        conn.commit()
        cursor.close()
    
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
        concepts = parse_concepts(args.input_file)
        write_to_db(concepts)
        sys.exit(0)
    except Exception as e:
        print(f"âŒ Error: {e}")
        sys.exit(1)
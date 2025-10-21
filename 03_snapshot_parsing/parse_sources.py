#!/usr/bin/env python3
"""Parse OpenAlex Sources"""
import json
import gzip
import psycopg2
from psycopg2.extras import execute_values
import pandas as pd
import argparse
import sys
from config import DB_CONFIG, BATCH_SIZE, PROGRESS_INTERVAL

def parse_sources(input_file):
    """Parse sources from gz file"""
    print(f"Reading {input_file}...")
    
    sources = []
    source_publishers = []
    unique_ids = set()
    
    with gzip.open(input_file, 'rt', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            if i % PROGRESS_INTERVAL == 0:
                print(f"  Processed {i:,} lines...")
            
            line = line.strip()
            if not line:
                continue
            
            try:
                source = json.loads(line)
            except:
                continue
            
            source_id = source.get('id', '').replace('https://openalex.org/', '')
            if not source_id or source_id in unique_ids:
                continue
            
            # Extract basic source info
            sources.append({
                'source_id': source_id,
                'display_name': source.get('display_name', ''),
                'issn_l': source.get('issn_l', ''),
                'host': '',
                'host_organization': '',
                'host_organization_lineage': '',
                'type': source.get('type', '')
            })
            unique_ids.add(source_id)
            
            # ========================================================================
            # EXTRACT PUBLISHER RELATIONSHIPS
            # ========================================================================
            
            publisher_info = None
            host_organization = source.get('host_organization')
            
            # Check for publisher field at top level
            if source.get('publisher'):
                publisher_info = source.get('publisher')
            
            # Check for publisher in host_organization if it's a dict
            elif isinstance(host_organization, dict) and host_organization.get('publisher'):
                publisher_info = host_organization.get('publisher')
            
            # Check for other possible publisher field names
            elif source.get('publisher_id'):
                publisher_info = source.get('publisher_id')
            
            # Process publisher information if found
            if publisher_info:
                publisher_id = None
                
                if isinstance(publisher_info, dict):
                    # If publisher is an object with id
                    publisher_id = publisher_info.get('id', '').replace('https://openalex.org/', '') if publisher_info.get('id') else ''
                
                elif isinstance(publisher_info, str):
                    # If publisher is just a string (URL or ID)
                    if publisher_info.startswith('https://openalex.org/'):
                        publisher_id = publisher_info.replace('https://openalex.org/', '')
                    elif publisher_info.startswith('P'):  # OpenAlex publisher IDs start with P
                        publisher_id = publisher_info
                
                # Create source-publisher relationship if we have both IDs
                if publisher_id and source_id:
                    source_publishers.append({
                        'source_id': source_id,
                        'publisher_id': publisher_id
                    })
    
    print(f"  Found {len(source_publishers):,} source-publisher relationships")
    return sources, source_publishers

def write_to_db(sources, source_publishers):
    """Write to database"""
    print("\nConnecting to database...")
    conn = psycopg2.connect(**DB_CONFIG)
    
    cursor = conn.cursor()
    cursor.execute("SET session_replication_role = replica;")
    conn.commit()
    cursor.close()
    
    if sources:
        print(f"Writing {len(sources):,} sources...")
        df = pd.DataFrame(sources).where(pd.notnull(pd.DataFrame(sources)), None)
        data = [tuple(row) for row in df.values]
        cursor = conn.cursor()
        sql = f"INSERT INTO sources ({','.join(df.columns)}) VALUES %s ON CONFLICT DO NOTHING"
        execute_values(cursor, sql, data, page_size=BATCH_SIZE)
        conn.commit()
        cursor.close()
    
    if source_publishers:
        print(f"Writing {len(source_publishers):,} source-publisher relationships...")
        df = pd.DataFrame(source_publishers).where(pd.notnull(pd.DataFrame(source_publishers)), None)
        data = [tuple(row) for row in df.values]
        cursor = conn.cursor()
        sql = f"INSERT INTO source_publishers ({','.join(df.columns)}) VALUES %s ON CONFLICT DO NOTHING"
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
        sources, source_publishers = parse_sources(args.input_file)
        write_to_db(sources, source_publishers)
        sys.exit(0)
    except Exception as e:
        print(f"âŒ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
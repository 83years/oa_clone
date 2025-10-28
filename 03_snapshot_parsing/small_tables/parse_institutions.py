#!/usr/bin/env python3
"""Parse OpenAlex Institutions"""
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

def parse_institutions(input_file):
    """Parse institutions from gz file"""
    print(f"Reading {input_file}...")
    
    institutions = []
    inst_hierarchy = []
    inst_geo = []
    unique_ids = set()
    
    with gzip.open(input_file, 'rt', encoding='utf-8') as f:
        for i, line in enumerate(f, 1):
            if i % PROGRESS_INTERVAL == 0:
                print(f"  Processed {i:,} lines...")
            
            line = line.strip()
            if not line:
                continue
            
            try:
                inst = json.loads(line)
            except:
                continue
            
            inst_id = (inst.get('id') or '').replace('https://openalex.org/', '')
            if not inst_id or inst_id in unique_ids:
                continue

            # Handle lineage
            lineage = inst.get('lineage', [])
            lineage_str = json.dumps([l.replace('https://openalex.org/', '') for l in lineage]) if lineage else ''

            if lineage and len(lineage) > 1:
                clean_lineage = [l.replace('https://openalex.org/', '') for l in lineage if l]
                
                # Create parent-child relationships
                for i in range(len(clean_lineage) - 1):
                    parent_id = clean_lineage[i]
                    child_id = clean_lineage[i + 1]
                    
                    # Only add if not the same institution (avoid self-reference)
                    if parent_id and child_id and parent_id != child_id:
                        inst_hierarchy.append({
                            'parent_institution_id': parent_id,
                            'child_institution_id': child_id,
                            'hierarchy_level': i + 1,
                            'relationship_type': 'direct_parent'
                        })

            # Extract IDs
            ids = inst.get('ids', {}) or {}
            
            # Extract summary stats
            summary_stats = inst.get('summary_stats', {}) or {}
            
            # Extract associated institutions
            associated = inst.get('associated_institutions', [])
            associated_str = json.dumps([a.get('id', '').replace('https://openalex.org/', '') 
                                        for a in associated if a.get('id')]) if associated else None
            
            # Main institution record
            institutions.append({
                'institution_id': inst_id,
                'display_name': inst.get('display_name', ''),
                'display_name_acronyms': json.dumps(inst.get('display_name_acronyms', [])) if inst.get('display_name_acronyms') else None,
                'display_name_alternatives': json.dumps(inst.get('display_name_alternatives', [])) if inst.get('display_name_alternatives') else None,
                'ror': (inst.get('ror') or '').replace('https://ror.org/', ''),
                'ror_id': (ids.get('ror') or '').replace('https://ror.org/', ''),
                'country_code': inst.get('country_code', ''),
                'type': (inst.get('type') or '').replace('https://openalex.org/institution-types/', ''),
                'lineage': lineage_str,
                'homepage_url': inst.get('homepage_url'),
                'image_url': inst.get('image_url'),
                'image_thumbnail_url': inst.get('image_thumbnail_url'),
                'works_count': inst.get('works_count'),
                'cited_by_count': inst.get('cited_by_count'),
                'created_date': inst.get('created_date'),
                'updated_date': inst.get('updated_date'),
                'openalex': ids.get('openalex'),
                'grid': (ids.get('grid') or '').replace('https://grid.ac/institutes/', ''),
                'wikipedia': ids.get('wikipedia'),
                'wikidata': (ids.get('wikidata') or '').replace('https://www.wikidata.org/wiki/', ''),
                'mag': ids.get('mag'),
                'summary_stats_2yr_mean_citedness': summary_stats.get('2yr_mean_citedness'),
                'summary_stats_h_index': summary_stats.get('h_index'),
                'summary_stats_i10_index': summary_stats.get('i10_index'),
                'associated_institutions': associated_str
            })
            
            # Geo data in separate table
            geo = inst.get('geo', {}) or {}
            if geo:
                inst_geo.append({
                    'institution_id': inst_id,
                    'city': geo.get('city'),
                    'geonames_city_id': geo.get('geonames_city_id'),
                    'region': geo.get('region'),
                    'country_code': geo.get('country_code'),
                    'country': geo.get('country'),
                    'latitude': geo.get('latitude'),
                    'longitude': geo.get('longitude')
                })
            
            unique_ids.add(inst_id)
    
    return institutions, inst_hierarchy, inst_geo

def write_to_db(institutions, inst_hierarchy, inst_geo):
    """Write to database"""
    print("\nConnecting to database...")
    conn = psycopg2.connect(**DB_CONFIG)
    
    cursor = conn.cursor()
    cursor.execute("SET session_replication_role = replica;")
    conn.commit()
    cursor.close()
    
    if institutions:
        print(f"Writing {len(institutions):,} institutions...")
        df = pd.DataFrame(institutions).where(pd.notnull(pd.DataFrame(institutions)), None)
        data = [tuple(row) for row in df.values]
        cursor = conn.cursor()
        sql = f"INSERT INTO institutions ({','.join(df.columns)}) VALUES %s ON CONFLICT DO NOTHING"
        execute_values(cursor, sql, data, page_size=BATCH_SIZE)
        conn.commit()
        cursor.close()
    
    if inst_hierarchy:
        print(f"Writing {len(inst_hierarchy):,} hierarchy relationships...")
        df = pd.DataFrame(inst_hierarchy).where(pd.notnull(pd.DataFrame(inst_hierarchy)), None)
        data = [tuple(row) for row in df.values]
        cursor = conn.cursor()
        sql = f"INSERT INTO institution_hierarchy ({','.join(df.columns)}) VALUES %s ON CONFLICT DO NOTHING"
        execute_values(cursor, sql, data, page_size=BATCH_SIZE)
        conn.commit()
        cursor.close()
    
    if inst_geo:
        print(f"Writing {len(inst_geo):,} geo records...")
        df = pd.DataFrame(inst_geo).where(pd.notnull(pd.DataFrame(inst_geo)), None)
        data = [tuple(row) for row in df.values]
        cursor = conn.cursor()
        sql = f"INSERT INTO institution_geo ({','.join(df.columns)}) VALUES %s ON CONFLICT DO NOTHING"
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
        institutions, inst_hierarchy, inst_geo = parse_institutions(args.input_file)
        write_to_db(institutions, inst_hierarchy, inst_geo)
        sys.exit(0)
    except Exception as e:
        print(f"âŒ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
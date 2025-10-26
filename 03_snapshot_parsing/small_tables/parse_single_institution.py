#!/usr/bin/env python3
"""
Parse a single institution from RTF file and insert into database
"""
import json
import re
import psycopg2
from psycopg2.extras import execute_values
import pandas as pd
import argparse
import sys
from config import DB_CONFIG

def extract_json_from_rtf(rtf_file):
    """Extract JSON data from RTF file - simple text extraction"""
    try:
        # Try using striprtf library if available
        from striprtf.striprtf import rtf_to_text
        with open(rtf_file, 'r', encoding='utf-8') as f:
            rtf_content = f.read()
        text = rtf_to_text(rtf_content)
    except ImportError:
        # Fallback: manual RTF text extraction
        with open(rtf_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Simple RTF parser: extract text between formatting codes
        # RTF formatting is \keyword or \keyword123 followed by space or delimiter
        # Text content is everything else except control sequences

        text_parts = []
        i = 0
        in_control_word = False
        skip_next = False

        while i < len(content):
            char = content[i]

            # Skip the RTF header section
            if i < 200 and char in ['{', '}', '\\']:
                if char == '\\':
                    # Find end of control word
                    j = i + 1
                    while j < len(content) and (content[j].isalnum() or content[j] in ['*', '-']):
                        j += 1
                    # Skip any following digits and delimiter
                    while j < len(content) and (content[j].isdigit() or content[j] == ' '):
                        j += 1
                    i = j
                    continue
                i += 1
                continue

            # Handle escape sequences
            if char == '\\':
                # Check if it's escaping a special char
                if i + 1 < len(content) and content[i + 1] in ['\\', '{', '}']:
                    text_parts.append(content[i + 1])
                    i += 2
                    continue

                # It's a control word - skip it
                j = i + 1
                # Skip letters
                while j < len(content) and content[j].isalpha():
                    j += 1
                # Skip optional numeric parameter
                if j < len(content) and content[j] == '-':
                    j += 1
                while j < len(content) and content[j].isdigit():
                    j += 1
                # Skip optional space delimiter
                if j < len(content) and content[j] == ' ':
                    j += 1
                i = j
                continue

            # Skip braces that are RTF structure
            if char in ['{', '}']:
                i += 1
                continue

            # It's regular text
            text_parts.append(char)
            i += 1

        text = ''.join(text_parts)

    # Clean and extract JSON
    text = text.strip()

    # Find the JSON object
    # Look for the pattern starting with {"id":"https://openalex.org/
    start_idx = text.find('{"id":"https://openalex.org/')
    if start_idx == -1:
        raise ValueError("Could not find JSON start in extracted text")

    # Find the matching closing brace
    brace_count = 0
    in_string = False
    escape_next = False
    end_idx = -1

    for i in range(start_idx, len(text)):
        char = text[i]

        if escape_next:
            escape_next = False
            continue

        if char == '\\':
            escape_next = True
            continue

        if char == '"' and not escape_next:
            in_string = not in_string
            continue

        if not in_string:
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i + 1
                    break

    if end_idx == -1:
        raise ValueError("Could not find JSON end in extracted text")

    json_str = text[start_idx:end_idx]

    # Clean up any remaining RTF artifacts that might have slipped through
    # Remove newlines that were left by RTF formatting - JSON doesn't need them
    # and they can appear in the middle of string values
    json_str = json_str.replace('\n', '').replace('\r', '')

    # Remove unicode escapes like \u0000
    json_str = re.sub(r'\\u0000', '', json_str)

    # Remove any other control characters
    json_str = ''.join(char for char in json_str if ord(char) >= 32 or char in ['\n', '\r', '\t'])

    # Try to parse
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        # Save for debugging
        with open('debug_extracted.txt', 'w', encoding='utf-8') as f:
            f.write(json_str)
        print(f"\nExtracted text saved to debug_extracted.txt for inspection")
        print(f"Error at position {e.pos}: {json_str[max(0, e.pos-50):e.pos+50]}")
        raise

def parse_institution(inst):
    """Parse institution JSON into database format"""
    institutions = []
    inst_hierarchy = []
    inst_geo = []

    inst_id = (inst.get('id') or '').replace('https://openalex.org/', '')
    if not inst_id:
        raise ValueError("Institution ID not found")

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
        print(f"Writing {len(institutions):,} institution(s)...")
        df = pd.DataFrame(institutions).where(pd.notnull(pd.DataFrame(institutions)), None)
        data = [tuple(row) for row in df.values]
        cursor = conn.cursor()
        sql = f"INSERT INTO institutions ({','.join(df.columns)}) VALUES %s ON CONFLICT (institution_id) DO NOTHING"
        execute_values(cursor, sql, data)
        print(f"  Institution: {institutions[0]['institution_id']} - {institutions[0]['display_name']}")
        conn.commit()
        cursor.close()

    if inst_hierarchy:
        print(f"Writing {len(inst_hierarchy):,} hierarchy relationship(s)...")
        df = pd.DataFrame(inst_hierarchy).where(pd.notnull(pd.DataFrame(inst_hierarchy)), None)
        data = [tuple(row) for row in df.values]
        cursor = conn.cursor()
        sql = f"INSERT INTO institution_hierarchy ({','.join(df.columns)}) VALUES %s ON CONFLICT DO NOTHING"
        execute_values(cursor, sql, data)
        conn.commit()
        cursor.close()

    if inst_geo:
        print(f"Writing {len(inst_geo):,} geo record(s)...")
        df = pd.DataFrame(inst_geo).where(pd.notnull(pd.DataFrame(inst_geo)), None)
        data = [tuple(row) for row in df.values]
        cursor = conn.cursor()
        sql = f"INSERT INTO institution_geo ({','.join(df.columns)}) VALUES %s ON CONFLICT (institution_id) DO NOTHING"
        execute_values(cursor, sql, data)
        conn.commit()
        cursor.close()

    cursor = conn.cursor()
    cursor.execute("SET session_replication_role = default;")
    conn.commit()
    cursor.close()
    conn.close()

    print("✅ Complete")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Parse single institution from RTF file')
    parser.add_argument('--input-file', required=True, help='Input RTF file')
    args = parser.parse_args()

    try:
        print(f"Reading {args.input_file}...")
        inst_json = extract_json_from_rtf(args.input_file)

        print(f"Parsing institution: {inst_json.get('display_name')}...")
        institutions, inst_hierarchy, inst_geo = parse_institution(inst_json)

        write_to_db(institutions, inst_hierarchy, inst_geo)
        sys.exit(0)

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

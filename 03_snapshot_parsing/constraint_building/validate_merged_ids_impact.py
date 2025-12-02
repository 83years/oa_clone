#!/usr/bin/env python3
"""
Quick validation: How many merged IDs would actually be applied?
Checks a sample of records against merged_ids to estimate impact.
"""
import sys
from pathlib import Path
SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PARENT_DIR))

import psycopg2
from config import DB_CONFIG
import gzip
import csv

MERGED_IDS_DIR = Path('/Volumes/OA_snapshot/24OCT2025/data/merged_ids')

def load_merged_ids_sample(entity_type, max_files=5):
    """Load a sample of merged IDs for quick validation"""
    entity_dir = MERGED_IDS_DIR / entity_type

    if not entity_dir.exists():
        print(f"⚠️  No merged_ids directory for {entity_type}")
        return {}

    csv_files = sorted(entity_dir.glob('*.csv.gz'))[:max_files]

    if not csv_files:
        print(f"⚠️  No merged_ids files found for {entity_type}")
        return {}

    merged_ids = {}

    for csv_file in csv_files:
        with gzip.open(csv_file, 'rt') as f:
            reader = csv.DictReader(f)
            for row in reader:
                old_id = row['merge_into_id']  # Deprecated ID
                new_id = row['id']              # Canonical ID
                merged_ids[old_id] = new_id

    return merged_ids


def check_table_for_merged_ids(conn, table, id_column, merged_ids, sample_size=100000):
    """
    Check how many records in a table have IDs that need updating.

    Args:
        table: Table name
        id_column: Column containing the ID to check
        merged_ids: Dict of old_id -> new_id mappings
        sample_size: How many records to check
    """
    cursor = conn.cursor()

    # Get total count
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    total_count = cursor.fetchone()[0]

    # Sample records
    cursor.execute(f"""
        SELECT {id_column}
        FROM {table}
        ORDER BY RANDOM()
        LIMIT {sample_size}
    """)

    sampled_ids = [row[0] for row in cursor.fetchall()]

    # Check how many are in merged_ids
    matches = [id for id in sampled_ids if id in merged_ids]

    match_rate = len(matches) / len(sampled_ids) if sampled_ids else 0
    estimated_total_matches = int(total_count * match_rate)

    cursor.close()

    return {
        'table': table,
        'column': id_column,
        'total_records': total_count,
        'sampled': len(sampled_ids),
        'matches_in_sample': len(matches),
        'match_rate': match_rate * 100,
        'estimated_total_matches': estimated_total_matches
    }


def main():
    print("="*70)
    print("MERGED IDs IMPACT VALIDATION")
    print("="*70)
    print("\nChecking merged_ids files...")

    # Load samples of merged IDs
    entity_types = ['authors', 'works', 'institutions', 'sources']
    all_merged_ids = {}

    for entity_type in entity_types:
        print(f"\nLoading {entity_type} merged_ids (first 5 files)...")
        merged_ids = load_merged_ids_sample(entity_type, max_files=5)
        all_merged_ids[entity_type] = merged_ids
        print(f"  Loaded {len(merged_ids):,} merged ID mappings")

    # Connect to test database
    print(f"\nConnecting to oadbv5_test...")
    db_config = DB_CONFIG.copy()
    db_config['database'] = 'oadbv5_test'
    conn = psycopg2.connect(**db_config)

    # Tables to check (using actual table names from database)
    tables_to_check = [
        # Works table
        ('works', 'work_id', all_merged_ids.get('works', {})),

        # Authorship relationships
        ('authorship', 'author_id', all_merged_ids.get('authors', {})),
        ('authorship', 'work_id', all_merged_ids.get('works', {})),
        ('authorship', 'institution_id', all_merged_ids.get('institutions', {})),

        # Work sources
        ('work_sources', 'work_id', all_merged_ids.get('works', {})),
        ('work_sources', 'source_id', all_merged_ids.get('sources', {})),

        # Author tables
        ('authors', 'author_id', all_merged_ids.get('authors', {})),
        ('authors_works_by_year', 'author_id', all_merged_ids.get('authors', {})),

        # Referenced works
        ('referenced_works', 'work_id', all_merged_ids.get('works', {})),
        ('referenced_works', 'referenced_work_id', all_merged_ids.get('works', {})),

        # Related works
        ('related_works', 'work_id', all_merged_ids.get('works', {})),
        ('related_works', 'related_work_id', all_merged_ids.get('works', {})),
    ]

    print("\n" + "="*70)
    print("CHECKING DATABASE TABLES (sample: 100k records per table)")
    print("="*70)

    results = []
    total_estimated_updates = 0

    for table, column, merged_ids in tables_to_check:
        if not merged_ids:
            print(f"\n⚠️  Skipping {table}.{column} - no merged_ids loaded")
            continue

        print(f"\nChecking {table}.{column}...")

        try:
            result = check_table_for_merged_ids(
                conn, table, column, merged_ids, sample_size=100000
            )
            results.append(result)

            print(f"  Total records: {result['total_records']:,}")
            print(f"  Sample size: {result['sampled']:,}")
            print(f"  Matches in sample: {result['matches_in_sample']:,}")
            print(f"  Match rate: {result['match_rate']:.2f}%")
            print(f"  📊 Estimated total needing update: {result['estimated_total_matches']:,}")

            total_estimated_updates += result['estimated_total_matches']

        except Exception as e:
            print(f"  ❌ Error: {e}")

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"\nTotal estimated ID updates needed: {total_estimated_updates:,}")

    if total_estimated_updates > 0:
        print("\n✓ RECOMMENDATION: Merged IDs phase is valuable - proceed with it")
        print(f"  {total_estimated_updates:,} records would be updated to canonical IDs")
    else:
        print("\n⚠️  RECOMMENDATION: Very few/no merged IDs found")
        print("  Consider skipping this phase to save time")

    # Detailed table
    if results:
        print("\n" + "="*70)
        print("DETAILED BREAKDOWN")
        print("="*70)
        print(f"{'Table':<30} {'Column':<20} {'Match %':<10} {'Est. Updates':<15}")
        print("-"*70)
        for r in results:
            print(f"{r['table']:<30} {r['column']:<20} {r['match_rate']:>8.2f}% {r['estimated_total_matches']:>12,}")

    conn.close()
    print("\n" + "="*70)


if __name__ == '__main__':
    main()

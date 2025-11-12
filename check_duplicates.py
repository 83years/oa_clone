#!/usr/bin/env python3
"""
Check for duplicate records in key tables
"""
import psycopg2
from config import DB_CONFIG

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    tables_to_check = [
        ('works', 'work_id'),
        ('authors', 'author_id'),
        ('institutions', 'institution_id'),
        ('sources', 'source_id'),
        ('topics', 'topic_id'),
        ('concepts', 'concept_id'),
        ('funders', 'funder_id'),
        ('publishers', 'publisher_id'),
        ('authorship', 'work_id, author_id'),
        ('work_topics', 'work_id, topic_id'),
        ('work_concepts', 'work_id, concept_id'),
        ('work_sources', 'work_id, source_id'),
        ('work_funders', 'work_id, funder_id, award_id'),
    ]

    print("="*80)
    print("DUPLICATE RECORDS CHECK")
    print("="*80)
    print(f"{'Table':<25} {'Total Rows':<15} {'Duplicates':<15} {'% Dup':<10}")
    print("-"*80)

    total_duplicates = 0

    for table_name, key_columns in tables_to_check:
        # Get total count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_count = cursor.fetchone()[0]

        # Get distinct count
        cursor.execute(f"SELECT COUNT(DISTINCT ({key_columns})) FROM {table_name}")
        distinct_count = cursor.fetchone()[0]

        duplicates = total_count - distinct_count
        total_duplicates += duplicates

        if duplicates > 0:
            pct = (duplicates / total_count * 100) if total_count > 0 else 0
            print(f"{table_name:<25} {total_count:<15,} {duplicates:<15,} {pct:>6.2f}%")
        else:
            print(f"{table_name:<25} {total_count:<15,} {'0':<15} {'0.00%':<10}")

    print("="*80)
    print(f"TOTAL DUPLICATE RECORDS ACROSS ALL TABLES: {total_duplicates:,}")
    print("="*80)

    cursor.close()
    conn.close()

except Exception as e:
    print(f"Error: {e}")

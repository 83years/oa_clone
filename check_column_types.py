#!/usr/bin/env python3
"""
Quick script to check the data types of columns that were changed
"""
import psycopg2
from config import DB_CONFIG

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # Check works table page columns
    cursor.execute("""
        SELECT column_name, data_type, character_maximum_length
        FROM information_schema.columns
        WHERE table_name = 'works'
        AND column_name IN ('first_page', 'last_page', 'biblio_first_page', 'biblio_last_page')
        ORDER BY column_name;
    """)

    print("="*70)
    print("WORKS TABLE - PAGE COLUMNS")
    print("="*70)
    print(f"{'Column Name':<25} {'Data Type':<20} {'Max Length':<15}")
    print("-"*70)

    for col_name, data_type, max_length in cursor.fetchall():
        length_str = str(max_length) if max_length else "N/A (TEXT)"
        print(f"{col_name:<25} {data_type:<20} {length_str:<15}")

    # Check work_funders table award_id column
    cursor.execute("""
        SELECT column_name, data_type, character_maximum_length
        FROM information_schema.columns
        WHERE table_name = 'work_funders'
        AND column_name = 'award_id';
    """)

    print("\n" + "="*70)
    print("WORK_FUNDERS TABLE - AWARD_ID COLUMN")
    print("="*70)
    print(f"{'Column Name':<25} {'Data Type':<20} {'Max Length':<15}")
    print("-"*70)

    for col_name, data_type, max_length in cursor.fetchall():
        length_str = str(max_length) if max_length else "N/A (TEXT)"
        print(f"{col_name:<25} {data_type:<20} {length_str:<15}")

    print("="*70)

    cursor.close()
    conn.close()

except Exception as e:
    print(f"Error: {e}")

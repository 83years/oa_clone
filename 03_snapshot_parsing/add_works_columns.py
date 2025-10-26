#!/usr/bin/env python3
"""
Add new columns to existing works table
Run this script to update your current database with the new columns
"""
import psycopg2
from datetime import datetime
from config import DB_CONFIG

def add_columns():
    """Add new columns to works table"""

    print(f"[{datetime.now()}] Connecting to database...")
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        print(f"[{datetime.now()}] Adding new columns to works table...")

        # Fix is_paratext from TEXT to BOOLEAN
        print("  - Converting is_paratext to BOOLEAN...")
        cursor.execute("ALTER TABLE works ALTER COLUMN is_paratext TYPE BOOLEAN USING CASE WHEN is_paratext IS NULL THEN FALSE ELSE is_paratext::boolean END;")

        # Add citation metrics
        print("  - Adding citation metric columns...")
        cursor.execute("ALTER TABLE works ADD COLUMN IF NOT EXISTS fwci DECIMAL(12,7);")
        cursor.execute("ALTER TABLE works ADD COLUMN IF NOT EXISTS citation_normalized_percentile_value DECIMAL(12,7);")
        cursor.execute("ALTER TABLE works ADD COLUMN IF NOT EXISTS citation_normalized_percentile_top_1_percent BOOLEAN;")
        cursor.execute("ALTER TABLE works ADD COLUMN IF NOT EXISTS citation_normalized_percentile_top_10_percent BOOLEAN;")
        cursor.execute("ALTER TABLE works ADD COLUMN IF NOT EXISTS cited_by_percentile_year_min INTEGER;")
        cursor.execute("ALTER TABLE works ADD COLUMN IF NOT EXISTS cited_by_percentile_year_max INTEGER;")

        # Add type and indexing metadata
        print("  - Adding type and indexing columns...")
        cursor.execute("ALTER TABLE works ADD COLUMN IF NOT EXISTS type_crossref VARCHAR(100);")
        cursor.execute("ALTER TABLE works ADD COLUMN IF NOT EXISTS indexed_in TEXT;")

        # Add count metadata
        print("  - Adding count metadata columns...")
        cursor.execute("ALTER TABLE works ADD COLUMN IF NOT EXISTS locations_count INTEGER;")
        cursor.execute("ALTER TABLE works ADD COLUMN IF NOT EXISTS authors_count INTEGER;")
        cursor.execute("ALTER TABLE works ADD COLUMN IF NOT EXISTS concepts_count INTEGER;")
        cursor.execute("ALTER TABLE works ADD COLUMN IF NOT EXISTS topics_count INTEGER;")
        cursor.execute("ALTER TABLE works ADD COLUMN IF NOT EXISTS has_fulltext BOOLEAN;")
        cursor.execute("ALTER TABLE works ADD COLUMN IF NOT EXISTS countries_distinct_count INTEGER;")
        cursor.execute("ALTER TABLE works ADD COLUMN IF NOT EXISTS institutions_distinct_count INTEGER;")

        # Add best OA location fields
        print("  - Adding best OA location columns...")
        cursor.execute("ALTER TABLE works ADD COLUMN IF NOT EXISTS best_oa_pdf_url TEXT;")
        cursor.execute("ALTER TABLE works ADD COLUMN IF NOT EXISTS best_oa_landing_page_url TEXT;")
        cursor.execute("ALTER TABLE works ADD COLUMN IF NOT EXISTS best_oa_is_oa BOOLEAN;")
        cursor.execute("ALTER TABLE works ADD COLUMN IF NOT EXISTS best_oa_version VARCHAR(100);")
        cursor.execute("ALTER TABLE works ADD COLUMN IF NOT EXISTS best_oa_license VARCHAR(100);")

        # Add primary location additional fields
        print("  - Adding primary location additional columns...")
        cursor.execute("ALTER TABLE works ADD COLUMN IF NOT EXISTS primary_location_is_accepted BOOLEAN;")
        cursor.execute("ALTER TABLE works ADD COLUMN IF NOT EXISTS primary_location_is_published BOOLEAN;")
        cursor.execute("ALTER TABLE works ADD COLUMN IF NOT EXISTS primary_location_pdf_url TEXT;")

        # Add language_id and fix mesh_id type
        print("  - Adding language_id and fixing mesh_id...")
        cursor.execute("ALTER TABLE works ADD COLUMN IF NOT EXISTS language_id VARCHAR(255);")
        cursor.execute("ALTER TABLE works ALTER COLUMN mesh_id TYPE TEXT;")

        conn.commit()

        # Verify columns added
        print(f"\n[{datetime.now()}] Verifying columns...")
        cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'works'
            ORDER BY ordinal_position;
        """)

        columns = cursor.fetchall()
        print(f"\nTotal columns in works table: {len(columns)}")
        print("\nNew columns added:")
        new_cols = [
            'fwci', 'citation_normalized_percentile_value',
            'citation_normalized_percentile_top_1_percent',
            'citation_normalized_percentile_top_10_percent',
            'cited_by_percentile_year_min', 'cited_by_percentile_year_max',
            'type_crossref', 'indexed_in', 'locations_count',
            'authors_count', 'concepts_count', 'topics_count', 'has_fulltext',
            'countries_distinct_count', 'institutions_distinct_count',
            'best_oa_pdf_url', 'best_oa_landing_page_url', 'best_oa_is_oa',
            'best_oa_version', 'best_oa_license',
            'primary_location_is_accepted', 'primary_location_is_published',
            'primary_location_pdf_url', 'language_id'
        ]

        for col_name, data_type in columns:
            if col_name in new_cols:
                print(f"  ✅ {col_name:50s} {data_type}")

        print(f"\n[{datetime.now()}] ✅ All columns added successfully!")

    except Exception as e:
        conn.rollback()
        print(f"\n[{datetime.now()}] ❌ Error adding columns: {e}")
        import traceback
        traceback.print_exc()
        raise

    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    add_columns()

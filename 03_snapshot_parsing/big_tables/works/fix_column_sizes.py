#!/usr/bin/env python3
"""
Fix VARCHAR column sizes in works table to handle longer values
"""
import psycopg2
import sys
from pathlib import Path

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
from config import DB_CONFIG

def fix_column_sizes():
    """Increase column sizes to prevent data truncation errors"""

    print("Connecting to database...")
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        print("\nFixing column sizes in works table...")

        # 1. Increase DOI column size
        print("  - Increasing doi from VARCHAR(255) to VARCHAR(500)...")
        cursor.execute("ALTER TABLE works ALTER COLUMN doi TYPE VARCHAR(500);")
        conn.commit()
        print("    ✅ doi updated")

        # 2. Change first_page to TEXT
        print("  - Changing first_page from VARCHAR(100) to TEXT...")
        cursor.execute("ALTER TABLE works ALTER COLUMN first_page TYPE TEXT;")
        conn.commit()
        print("    ✅ first_page updated")

        # 3. Change last_page to TEXT
        print("  - Changing last_page from VARCHAR(100) to TEXT...")
        cursor.execute("ALTER TABLE works ALTER COLUMN last_page TYPE TEXT;")
        conn.commit()
        print("    ✅ last_page updated")

        # 4. Change biblio_first_page to TEXT (for consistency)
        print("  - Changing biblio_first_page to TEXT...")
        cursor.execute("ALTER TABLE works ALTER COLUMN biblio_first_page TYPE TEXT;")
        conn.commit()
        print("    ✅ biblio_first_page updated")

        # 5. Change biblio_last_page to TEXT (for consistency)
        print("  - Changing biblio_last_page to TEXT...")
        cursor.execute("ALTER TABLE works ALTER COLUMN biblio_last_page TYPE TEXT;")
        conn.commit()
        print("    ✅ biblio_last_page updated")

        # Verify changes
        print("\n" + "="*70)
        print("Verifying column changes:")
        print("="*70)

        cursor.execute("""
            SELECT
                column_name,
                data_type,
                character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'works'
            AND column_name IN ('doi', 'first_page', 'last_page', 'biblio_first_page', 'biblio_last_page')
            ORDER BY column_name;
        """)

        print(f"\n{'Column Name':<25} {'Data Type':<20} {'Max Length':<15}")
        print("-" * 70)
        for row in cursor.fetchall():
            col_name, data_type, max_length = row
            max_length_str = str(max_length) if max_length else "unlimited"
            print(f"{col_name:<25} {data_type:<20} {max_length_str:<15}")

        print("\n" + "="*70)
        print("✅ All column sizes updated successfully!")
        print("="*70)

        print("\nYou can now retry the failed files:")
        print("  - 2024-12-12/part_004.gz")
        print("  - 2025-01-23/part_000.gz")
        print("  - 2025-01-24/part_009.gz")
        print("  - 2025-04-16/part_000.gz")
        print("  - 2025-06-10/part_000.gz")
        print("  - 2025-06-10/part_001.gz")
        print("  - 2025-06-11/part_000.gz")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    fix_column_sizes()

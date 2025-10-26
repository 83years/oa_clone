#!/usr/bin/env python3
"""
Fix cited_by_percentile_year columns from INTEGER to DECIMAL
This script alters the works table to fix the data type mismatch
"""
import psycopg2
from config import DB_CONFIG

def fix_percentile_columns():
    """Alter the cited_by_percentile_year columns to DECIMAL type"""
    print("Connecting to database...")
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()

    try:
        print("\nFixing cited_by_percentile_year_min column...")
        cursor.execute("""
            ALTER TABLE works
            ALTER COLUMN cited_by_percentile_year_min TYPE DECIMAL(5,2);
        """)
        print("✅ cited_by_percentile_year_min changed to DECIMAL(5,2)")

        print("\nFixing cited_by_percentile_year_max column...")
        cursor.execute("""
            ALTER TABLE works
            ALTER COLUMN cited_by_percentile_year_max TYPE DECIMAL(5,2);
        """)
        print("✅ cited_by_percentile_year_max changed to DECIMAL(5,2)")

        conn.commit()

        # Verify the changes
        print("\nVerifying column types...")
        cursor.execute("""
            SELECT
                column_name,
                data_type,
                numeric_precision,
                numeric_scale
            FROM information_schema.columns
            WHERE table_name = 'works'
                AND column_name IN ('cited_by_percentile_year_min', 'cited_by_percentile_year_max')
            ORDER BY column_name;
        """)

        results = cursor.fetchall()
        print("\nColumn definitions:")
        for row in results:
            print(f"  {row[0]}: {row[1]}({row[2]},{row[3]})")

        print("\n✅ Fix completed successfully!")
        print("\nYou can now resume the orchestrator:")
        print("  python big_orchestrator.py")

    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    fix_percentile_columns()

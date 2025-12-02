#!/usr/bin/env python3
"""
Count rows in the authorship table of OADB database
"""
import sys
from pathlib import Path
import psycopg2

SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PARENT_DIR))

from config import DB_CONFIG


def count_authorship_rows():
    """Count and display the number of rows in the authorship table"""

    # Connect to oadbv5 database
    db_config = DB_CONFIG.copy()
    db_config['database'] = 'oadbv5'

    conn = psycopg2.connect(**db_config)
    cursor = conn.cursor()

    try:
        # Count rows in authorship table
        cursor.execute("SELECT COUNT(*) FROM authorship")
        count = cursor.fetchone()[0]

        print(f"\nAuthorship table row count: {count:,}")
        print()

    except Exception as e:
        print(f"Error counting rows: {e}")
        sys.exit(1)

    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    count_authorship_rows()

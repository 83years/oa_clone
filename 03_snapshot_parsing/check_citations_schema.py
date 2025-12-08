#!/usr/bin/env python3
"""Check citations_by_year table schema"""
import psycopg2
import sys
from pathlib import Path

# Add parent directory to path for config imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DB_CONFIG

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

# Get column names
cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'citations_by_year'
    ORDER BY ordinal_position
""")

print("\ncitations_by_year table schema:")
print("="*50)
for row in cur.fetchall():
    print(f"  {row[0]:<30s} {row[1]}")

# Get sample data
print("\nSample data:")
print("="*50)
cur.execute("SELECT * FROM citations_by_year LIMIT 5")
for row in cur.fetchall():
    print(row)

cur.close()
conn.close()

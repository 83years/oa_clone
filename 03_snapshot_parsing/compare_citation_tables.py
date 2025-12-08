#!/usr/bin/env python3
"""Compare citations and referenced_works tables"""
import psycopg2
import sys
from pathlib import Path

# Add parent directory to path for config imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DB_CONFIG

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

print("\n" + "="*80)
print("CITATIONS vs REFERENCED_WORKS TABLE COMPARISON")
print("="*80)

# Check if citations table exists and its schema
print("\n1. CITATIONS TABLE:")
print("-" * 80)
cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'citations'
    ORDER BY ordinal_position
""")
citations_cols = cur.fetchall()
if citations_cols:
    for col, dtype in citations_cols:
        print(f"  {col:<30s} {dtype}")

    # Get count
    cur.execute("SELECT COUNT(*) FROM citations")
    print(f"\nTotal records: {cur.fetchone()[0]:,}")

    # Sample data
    print("\nSample data:")
    cur.execute("SELECT * FROM citations LIMIT 5")
    for row in cur.fetchall():
        print(f"  {row}")
else:
    print("  Table does not exist or has no columns")

# Check referenced_works table
print("\n2. REFERENCED_WORKS TABLE:")
print("-" * 80)
cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'referenced_works'
    ORDER BY ordinal_position
""")
ref_cols = cur.fetchall()
for col, dtype in ref_cols:
    print(f"  {col:<30s} {dtype}")

# Get count
cur.execute("SELECT COUNT(*) FROM referenced_works")
print(f"\nTotal records: {cur.fetchone()[0]:,}")

# Sample data
print("\nSample data:")
cur.execute("SELECT * FROM referenced_works LIMIT 5")
for row in cur.fetchall():
    print(f"  {row}")

# Check citations_by_year table
print("\n3. CITATIONS_BY_YEAR TABLE:")
print("-" * 80)
cur.execute("""
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'citations_by_year'
    ORDER BY ordinal_position
""")
cby_cols = cur.fetchall()
for col, dtype in cby_cols:
    print(f"  {col:<30s} {dtype}")

# Get count
cur.execute("SELECT COUNT(*) FROM citations_by_year")
print(f"\nTotal records: {cur.fetchone()[0]:,}")

# Sample data
print("\nSample data:")
cur.execute("SELECT * FROM citations_by_year LIMIT 5")
for row in cur.fetchall():
    print(f"  {row}")

print("\n" + "="*80)
print("ANALYSIS:")
print("="*80)

if citations_cols:
    print("""
citations table:
  - Appears to be a direct relationship table
  - Maps citing_work_id -> cited_work_id
  - Represents the citation network graph edges

referenced_works table:
  - Also maps work_id -> referenced_work_id
  - Extracted from works 'referenced_works' field
  - Represents which works cite which works (same as citations?)

citations_by_year table:
  - Time-series citation data
  - Shows how many times a work was cited in each year
  - Different purpose from the other two tables

CONCLUSION:
  If citations and referenced_works contain the same data (work A cites work B),
  then one is redundant. Need to check if they're identical.
""")
else:
    print("""
citations table:
  - Does NOT exist in the database

referenced_works table:
  - Extracted from works 'referenced_works' field
  - Maps work_id -> referenced_work_id
  - Represents which works cite which works

citations_by_year table:
  - Time-series citation data from works 'counts_by_year'
  - Shows citation counts per work per year
  - Different data than referenced_works

CONCLUSION:
  The 'citations' table does not exist in this database.
  Only 'referenced_works' and 'citations_by_year' exist.
""")

print("="*80 + "\n")

cur.close()
conn.close()

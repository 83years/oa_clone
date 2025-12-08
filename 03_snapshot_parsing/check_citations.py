#!/usr/bin/env python3
"""Check citations_by_year data sample"""
import psycopg2
import sys
from pathlib import Path

# Add parent directory to path for config imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import DB_CONFIG

conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

print("\n" + "="*70)
print("CITATIONS_BY_YEAR DATA SAMPLE")
print("="*70)

# Get sample of citations data
cur.execute("""
    SELECT work_id, year, citation_count
    FROM citations_by_year
    ORDER BY citation_count DESC
    LIMIT 20
""")

print(f"\n{'Work ID':<20s} {'Year':<8s} {'Citations':>12s}")
print("-" * 70)

for row in cur.fetchall():
    work_id, year, cited_by = row
    print(f"{work_id:<20s} {year:<8d} {cited_by:>12,}")

# Get year distribution
print("\n" + "="*70)
print("CITATIONS BY YEAR DISTRIBUTION")
print("="*70)

cur.execute("""
    SELECT year, COUNT(*) as works_with_citations, SUM(citation_count) as total_citations
    FROM citations_by_year
    GROUP BY year
    ORDER BY year DESC
    LIMIT 20
""")

print(f"\n{'Year':<8s} {'Works':>12s} {'Total Citations':>18s}")
print("-" * 70)

for row in cur.fetchall():
    year, works, citations = row
    print(f"{year:<8d} {works:>12,} {citations:>18,}")

print("="*70 + "\n")

cur.close()
conn.close()

#!/usr/bin/env python3
"""Quick script to check database table counts"""
import psycopg2
import os

DB_CONFIG = {
    'host': '192.168.1.100',
    'port': 55432,
    'database': 'oadb2',
    'user': 'admin',
    'password': os.getenv('ADMIN_PASSWORD', 'secure_password_123')
}

# Connect to database
conn = psycopg2.connect(**DB_CONFIG)
cur = conn.cursor()

# List of tables to check
tables = [
    'topics', 'topic_hierarchy', 'concepts', 'publishers', 'funders',
    'sources', 'source_publishers', 'institutions', 'institution_geo', 'institution_hierarchy',
    'authors', 'author_topics', 'author_concepts', 'author_institutions', 'authors_works_by_year',
    'works', 'authorship', 'work_topics', 'work_concepts', 'work_sources',
    'work_keywords', 'work_funders', 'citations_by_year', 'referenced_works', 'related_works'
]

print("\n" + "="*70)
print("DATABASE TABLE COUNTS")
print("="*70)

total_records = 0
for table in tables:
    cur.execute(f"SELECT COUNT(*) FROM {table}")
    count = cur.fetchone()[0]
    total_records += count
    print(f"  {table:25s} {count:>12,}")

print("="*70)
print(f"  TOTAL RECORDS:           {total_records:>12,}")
print("="*70 + "\n")

cur.close()
conn.close()

#!/usr/bin/env python3
"""Check citations_by_year table schema"""
import psycopg2
import os

DB_CONFIG = {
    'host': '192.168.1.100',
    'port': 55432,
    'database': 'oadb2',
    'user': 'admin',
    'password': os.getenv('ADMIN_PASSWORD', 'secure_password_123')
}

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

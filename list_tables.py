#!/usr/bin/env python3
import psycopg2
from config import DB_CONFIG

db_config = DB_CONFIG.copy()
db_config['database'] = 'OADB_test'

conn = psycopg2.connect(**db_config)
cursor = conn.cursor()

# List all tables
cursor.execute("""
    SELECT table_name,
           pg_size_pretty(pg_total_relation_size(quote_ident(table_name)::regclass)) as size
    FROM information_schema.tables
    WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
    ORDER BY pg_total_relation_size(quote_ident(table_name)::regclass) DESC
    LIMIT 30
""")

print("="*70)
print("TABLES IN OADB_test (top 30 by size)")
print("="*70)
print(f"{'Table Name':<40} {'Size':<15}")
print("-"*70)

for table, size in cursor.fetchall():
    print(f"{table:<40} {size:<15}")

cursor.close()
conn.close()

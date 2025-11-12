#!/usr/bin/env python3
import psycopg2
from config import DB_CONFIG

# Test connecting to OADB_test
test_config = DB_CONFIG.copy()
test_config['database'] = 'OADB_test'

print(f"Attempting to connect to: {test_config}")

try:
    conn = psycopg2.connect(**test_config)
    print("✓ Successfully connected to OADB_test!")

    cursor = conn.cursor()
    cursor.execute("SELECT current_database(), pg_size_pretty(pg_database_size(current_database()))")
    db_name, size = cursor.fetchone()
    print(f"  Database: {db_name}")
    print(f"  Size: {size}")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"✗ Connection failed: {e}")

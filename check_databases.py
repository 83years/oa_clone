#!/usr/bin/env python3
"""
Quick script to list all databases on the PostgreSQL server
"""
import psycopg2
from config import DB_CONFIG

# Connect to the default 'postgres' database to list all databases
conn_config = DB_CONFIG.copy()
conn_config['database'] = 'postgres'  # Connect to default database

try:
    conn = psycopg2.connect(**conn_config)
    cursor = conn.cursor()

    # List all databases
    cursor.execute("""
        SELECT datname, pg_size_pretty(pg_database_size(datname)) as size
        FROM pg_database
        WHERE datistemplate = false
        ORDER BY datname;
    """)

    databases = cursor.fetchall()

    print("="*70)
    print("DATABASES ON SERVER {}:{}".format(DB_CONFIG['host'], DB_CONFIG['port']))
    print("="*70)
    print(f"{'Database Name':<30} {'Size':<20}")
    print("-"*70)

    for db_name, size in databases:
        print(f"{db_name:<30} {size:<20}")

    print("="*70)

    # Check specifically for our databases
    db_names = [db[0] for db in databases]

    print("\nChecking for expected databases:")
    for expected in ['OADB', 'OADB_test', 'oadb2', 'oadb2_test']:
        if expected in db_names:
            print(f"  ✓ {expected} EXISTS")
        else:
            print(f"  ✗ {expected} NOT FOUND")

    cursor.close()
    conn.close()

except Exception as e:
    print(f"Error: {e}")

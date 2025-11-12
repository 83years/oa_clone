#!/usr/bin/env python3
"""
Create OADB_test database by copying OADB
Terminates blocking connections first
"""
import psycopg2
from config import DB_CONFIG
import time

# Connect to postgres database (not OADB)
conn_config = DB_CONFIG.copy()
conn_config['database'] = 'postgres'

print("="*70)
print("CREATE OADB_test DATABASE")
print("="*70)

try:
    # Need to set autocommit for database creation
    conn = psycopg2.connect(**conn_config)
    conn.autocommit = True
    cursor = conn.cursor()

    print("\nStep 1: Checking for existing connections to OADB...")
    cursor.execute("""
        SELECT pid, usename, application_name, state
        FROM pg_stat_activity
        WHERE datname = 'OADB' AND pid <> pg_backend_pid()
    """)

    connections = cursor.fetchall()

    if connections:
        print(f"Found {len(connections)} active connections to OADB:")
        for pid, user, app, state in connections:
            print(f"  - PID {pid}: {user} ({app}) - {state}")

        print("\nStep 2: Terminating these connections...")
        cursor.execute("""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = 'OADB' AND pid <> pg_backend_pid()
        """)

        terminated = cursor.fetchall()
        print(f"Terminated {len(terminated)} connections")

        # Wait a moment for cleanup
        time.sleep(2)
    else:
        print("No active connections found - good to proceed!")

    print("\nStep 3: Checking if OADB_test already exists...")
    cursor.execute("""
        SELECT 1 FROM pg_database WHERE datname = 'OADB_test'
    """)

    if cursor.fetchone():
        print("WARNING: OADB_test already exists!")
        print("Dropping existing OADB_test database...")

        # Terminate any connections to OADB_test
        cursor.execute("""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = 'OADB_test' AND pid <> pg_backend_pid()
        """)

        time.sleep(1)

        cursor.execute('DROP DATABASE "OADB_test"')
        print("Dropped OADB_test")

    print("\nStep 4: Creating OADB_test from OADB template...")
    print("="*70)
    print("⚠️  STARTING: This will copy 1,012 GB of data!")
    print("   This operation may take MANY HOURS (possibly 6-24 hours)")
    print("   depending on your disk speed.")
    print("="*70)

    print("\nCreating database... (this will take a LONG time)")
    print("Started at:", time.strftime("%Y-%m-%d %H:%M:%S"))

    start_time = time.time()

    # Create the database
    cursor.execute('CREATE DATABASE "OADB_test" WITH TEMPLATE "OADB" OWNER admin')

    elapsed = time.time() - start_time
    hours = int(elapsed // 3600)
    minutes = int((elapsed % 3600) // 60)

    print(f"\n✓ Database created successfully!")
    print(f"Completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Time taken: {hours}h {minutes}m")

    # Verify it exists
    cursor.execute("""
        SELECT pg_size_pretty(pg_database_size('OADB_test'))
    """)

    size = cursor.fetchone()[0]
    print(f"Database size: {size}")

    cursor.close()
    conn.close()

    print("\n" + "="*70)
    print("SUCCESS! OADB_test is ready for constraint building")
    print("="*70)

except psycopg2.errors.ObjectInUse as e:
    print(f"\n❌ ERROR: OADB is still being accessed by other users")
    print("Please close all connections to OADB and try again")
    print(f"Details: {e}")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

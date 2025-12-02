#!/usr/bin/env python3
"""
Test primary key creation on a single small table to estimate timing.
"""
import sys
from pathlib import Path
SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PARENT_DIR))

import psycopg2
from config import DB_CONFIG
import time
from datetime import datetime

def log(message):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(f"[{timestamp}] {message}")

def get_table_info(conn, table_name):
    """Get size and row count for a table"""
    cursor = conn.cursor()

    cursor.execute(f"""
        SELECT
            pg_size_pretty(pg_total_relation_size('{table_name}'::regclass)) as size,
            COUNT(*) as row_count
        FROM {table_name}
    """)

    size, row_count = cursor.fetchone()
    cursor.close()

    return size, row_count

def check_existing_pk(conn, table_name):
    """Check if primary key already exists"""
    cursor = conn.cursor()

    cursor.execute(f"""
        SELECT constraint_name
        FROM information_schema.table_constraints
        WHERE table_name = '{table_name}'
        AND constraint_type = 'PRIMARY KEY'
    """)

    result = cursor.fetchone()
    cursor.close()

    return result[0] if result else None

def create_primary_key(conn, table_name, pk_column):
    """Create primary key on a table and time it"""
    cursor = conn.cursor()

    log(f"Creating PRIMARY KEY on {table_name}({pk_column})...")

    pk_name = f"{table_name}_pkey"

    start_time = time.time()

    try:
        cursor.execute(f"""
            ALTER TABLE {table_name}
            ADD CONSTRAINT {pk_name}
            PRIMARY KEY ({pk_column})
        """)
        conn.commit()

        elapsed = time.time() - start_time
        log(f"✓ PRIMARY KEY created in {elapsed:.2f} seconds")

        cursor.close()
        return True, elapsed

    except Exception as e:
        conn.rollback()
        elapsed = time.time() - start_time
        log(f"✗ Failed after {elapsed:.2f} seconds: {e}")
        cursor.close()
        return False, elapsed

def main():
    # Test tables from smallest to largest
    test_tables = [
        ('publishers', 'publisher_id'),
        ('topics', 'topic_id'),
        ('funders', 'funder_id'),
        ('institutions', 'institution_id'),
    ]

    log("="*70)
    log("PRIMARY KEY CREATION TIMING TEST")
    log("="*70)

    # Connect to test database
    db_config = DB_CONFIG.copy()
    db_config['database'] = 'oadbv5_test'

    log(f"\nConnecting to {db_config['database']}...")
    conn = psycopg2.connect(**db_config)

    results = []

    for table_name, pk_column in test_tables:
        log(f"\n{'='*70}")
        log(f"TABLE: {table_name}")
        log(f"{'='*70}")

        # Get table info
        try:
            size, row_count = get_table_info(conn, table_name)
            log(f"Size: {size}")
            log(f"Rows: {row_count:,}")
        except Exception as e:
            log(f"✗ Table not found or error: {e}")
            continue

        # Check for existing PK
        existing_pk = check_existing_pk(conn, table_name)
        if existing_pk:
            log(f"⚠️  Primary key already exists: {existing_pk}")
            log(f"   Skipping...")
            continue

        # Create PK and time it
        success, elapsed = create_primary_key(conn, table_name, pk_column)

        if success:
            # Calculate throughput
            rows_per_sec = row_count / elapsed if elapsed > 0 else 0

            results.append({
                'table': table_name,
                'size': size,
                'rows': row_count,
                'time_seconds': elapsed,
                'rows_per_second': rows_per_sec
            })

    conn.close()

    # Summary and projections
    if results:
        log(f"\n{'='*70}")
        log("TIMING RESULTS & PROJECTIONS")
        log(f"{'='*70}")

        log(f"\n{'Table':<20} {'Rows':>12} {'Time (s)':>10} {'Rows/sec':>12}")
        log("-"*70)

        for r in results:
            log(f"{r['table']:<20} {r['rows']:>12,} {r['time_seconds']:>10.2f} {r['rows_per_second']:>12,.0f}")

        # Calculate average throughput
        avg_rows_per_sec = sum(r['rows_per_second'] for r in results) / len(results)

        log(f"\n{'='*70}")
        log("TIME ESTIMATES FOR LARGE TABLES")
        log(f"{'='*70}")
        log(f"Average throughput: {avg_rows_per_sec:,.0f} rows/second\n")

        # Estimate for big tables (approximate row counts)
        big_tables = [
            ('authors', 115_000_000),
            ('work_sources', 277_000_000),
            ('authorship', 1_100_000_000),
            ('work_concepts', 2_300_000_000),
            ('works', 277_000_000),
        ]

        log(f"{'Table':<20} {'Est. Rows':>15} {'Est. Time':>15}")
        log("-"*70)

        total_estimated_seconds = 0

        for table, est_rows in big_tables:
            est_time_sec = est_rows / avg_rows_per_sec
            est_time_min = est_time_sec / 60
            est_time_hrs = est_time_min / 60

            total_estimated_seconds += est_time_sec

            if est_time_hrs > 1:
                time_str = f"{est_time_hrs:.1f} hours"
            elif est_time_min > 1:
                time_str = f"{est_time_min:.1f} minutes"
            else:
                time_str = f"{est_time_sec:.0f} seconds"

            log(f"{table:<20} {est_rows:>15,} {time_str:>15}")

        total_hrs = total_estimated_seconds / 3600
        log(f"\n{'TOTAL ESTIMATED TIME':<20} {'':<15} {total_hrs:.1f} hours")

        log(f"\n{'='*70}")
        log("Note: These are rough estimates. Actual times may vary based on:")
        log("  - Existing indexes")
        log("  - Data distribution")
        log("  - Disk I/O performance")
        log("  - Concurrent database activity")
        log(f"{'='*70}")

    else:
        log("\n⚠️  No results - all tables already have primary keys or errors occurred")

if __name__ == '__main__':
    main()

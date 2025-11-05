#!/usr/bin/env python3
"""
Simple script to check the row count for each table in the PostgreSQL database.
This is a lightweight, read-only operation that won't impact ongoing parsing.
"""

import psycopg2
from psycopg2 import sql
import os
import sys

# Database configuration
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '192.168.1.100'),
    'port': int(os.getenv('DB_PORT', '55432')),
    'database': os.getenv('DB_NAME', 'OADB'),
    'user': os.getenv('DB_USER', 'admin'),
    'password': os.getenv('DB_PASSWORD', 'secure_password_123')
}


def get_table_sizes(conn):
    """
    Get row counts for all tables in the database.
    Uses efficient COUNT(*) queries that read from table statistics.
    """
    cursor = conn.cursor()

    # Get list of all user tables (excluding system tables)
    cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_type = 'BASE TABLE'
        ORDER BY table_name;
    """)

    tables = [row[0] for row in cursor.fetchall()]

    if not tables:
        print("No tables found in the database.")
        return []

    results = []

    print(f"\nAnalyzing {len(tables)} tables...\n")

    for table in tables:
        # Use simple COUNT(*) - PostgreSQL optimizes this well
        query = sql.SQL("SELECT COUNT(*) FROM {}").format(
            sql.Identifier(table)
        )

        cursor.execute(query)
        count = cursor.fetchone()[0]

        results.append({
            'table': table,
            'row_count': count
        })

        # Print progress
        print(f"  {table}: {count:,} rows")

    cursor.close()
    return results


def print_summary(results):
    """Print summary statistics."""
    if not results:
        return

    print("\n" + "="*60)
    print("SUMMARY STATISTICS")
    print("="*60)

    total_rows = sum(r['row_count'] for r in results)
    print(f"Total tables: {len(results)}")
    print(f"Total rows across all tables: {total_rows:,}")

    # Find largest tables
    sorted_results = sorted(results, key=lambda x: x['row_count'], reverse=True)

    print("\nTop 10 largest tables:")
    for i, result in enumerate(sorted_results[:10], 1):
        pct = (result['row_count'] / total_rows * 100) if total_rows > 0 else 0
        print(f"  {i:2d}. {result['table']:30s}: {result['row_count']:12,} rows ({pct:5.1f}%)")

    # Find empty tables
    empty_tables = [r['table'] for r in results if r['row_count'] == 0]
    if empty_tables:
        print(f"\nEmpty tables ({len(empty_tables)}):")
        for table in empty_tables:
            print(f"  - {table}")


def main():
    """Main execution function."""
    print("Connecting to PostgreSQL database...")

    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print(f"Connected to database: {DB_CONFIG['database']} at {DB_CONFIG['host']}:{DB_CONFIG['port']}")

        # Get table sizes
        results = get_table_sizes(conn)

        # Print summary
        print_summary(results)

        # Optional: save to CSV
        try:
            import csv
            output_file = 'database_table_sizes.csv'
            with open(output_file, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=['table', 'row_count'])
                writer.writeheader()
                writer.writerows(results)
            print(f"\nDetailed results saved to: {output_file}")
        except Exception as e:
            print(f"\nNote: Could not save CSV file: {e}")

        conn.close()
        print("\nAnalysis complete. Database connection closed.")

    except psycopg2.Error as e:
        print(f"Database error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

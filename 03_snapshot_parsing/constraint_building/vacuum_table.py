#!/usr/bin/env python3
"""
VACUUM ANALYZE Database Tables
Checks for database activity and runs VACUUM ANALYZE on specified tables
to reclaim space and update statistics after row deletions.
"""
import sys
from pathlib import Path
from datetime import datetime
import psycopg2
import argparse
import time

SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PARENT_DIR))

from config import DB_CONFIG


class VacuumManager:
    """Manages VACUUM ANALYZE operations on database tables"""

    def __init__(self, test_mode=False):
        """
        Initialize vacuum manager

        Args:
            test_mode: Use test database (oadbv5_test)
        """
        self.test_mode = test_mode
        db_config = DB_CONFIG.copy()
        if test_mode:
            db_config['database'] = 'oadbv5_test'

        self.conn = psycopg2.connect(**db_config)
        self.conn.autocommit = True  # Required for VACUUM
        self.cursor = self.conn.cursor()

        # Set up file logging
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = log_dir / f'vacuum_table_{timestamp}.log'

        self.log(f"Connected to database: {db_config['database']}")
        self.log(f"Log file: {self.log_file}")

    def log(self, message):
        """Print timestamped message to console and file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] {message}"
        print(log_line)

        # Also write to file
        with open(self.log_file, 'a') as f:
            f.write(log_line + '\n')

    def check_table_exists(self, table_name):
        """
        Check if table exists in database

        Args:
            table_name: Name of the table

        Returns:
            bool: True if table exists, False otherwise
        """
        self.cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = %s
            )
        """, (table_name,))

        return self.cursor.fetchone()[0]

    def get_database_activity(self):
        """
        Check for active database connections and queries

        Returns:
            dict: Activity statistics including active queries, idle connections, etc.
        """
        self.log("\nChecking database activity...")

        # Get active connections
        self.cursor.execute("""
            SELECT
                state,
                COUNT(*) as count
            FROM pg_stat_activity
            WHERE datname = current_database()
            GROUP BY state
        """)

        activity = {}
        for row in self.cursor.fetchall():
            state = row[0] or 'NULL'
            count = row[1]
            activity[state] = count

        # Get active queries (excluding this connection)
        self.cursor.execute("""
            SELECT
                COUNT(*) as active_queries
            FROM pg_stat_activity
            WHERE datname = current_database()
            AND state = 'active'
            AND pid != pg_backend_pid()
        """)

        active_queries = self.cursor.fetchone()[0]
        activity['active_queries_excluding_self'] = active_queries

        return activity

    def display_activity(self, activity):
        """
        Display database activity information

        Args:
            activity: Dictionary of activity statistics
        """
        self.log("Database Activity:")
        for state, count in sorted(activity.items()):
            self.log(f"  {state}: {count}")

        if activity.get('active_queries_excluding_self', 0) > 0:
            self.log(f"\n⚠️  WARNING: {activity['active_queries_excluding_self']} active queries detected")
            self.log("  VACUUM will run concurrently but may be slower")
        else:
            self.log("\n✅ No active queries detected - optimal for VACUUM")

    def get_table_stats(self, table_name):
        """
        Get statistics about a table before VACUUM

        Args:
            table_name: Name of the table

        Returns:
            dict: Table statistics
        """
        # Get dead tuples and bloat information
        self.cursor.execute("""
            SELECT
                n_live_tup,
                n_dead_tup,
                last_vacuum,
                last_autovacuum,
                last_analyze,
                last_autoanalyze
            FROM pg_stat_user_tables
            WHERE relname = %s
        """, (table_name,))

        result = self.cursor.fetchone()
        if not result:
            return None

        stats = {
            'live_tuples': result[0],
            'dead_tuples': result[1],
            'last_vacuum': result[2],
            'last_autovacuum': result[3],
            'last_analyze': result[4],
            'last_autoanalyze': result[5]
        }

        # Get table size
        self.cursor.execute("""
            SELECT pg_size_pretty(pg_total_relation_size(%s))
        """, (table_name,))

        stats['total_size'] = self.cursor.fetchone()[0]

        return stats

    def display_table_stats(self, table_name, stats):
        """
        Display table statistics

        Args:
            table_name: Name of the table
            stats: Dictionary of table statistics
        """
        self.log(f"\nTable Statistics for '{table_name}':")
        self.log(f"  Total size: {stats['total_size']}")
        self.log(f"  Live tuples: {stats['live_tuples']:,}")
        self.log(f"  Dead tuples: {stats['dead_tuples']:,}")

        if stats['dead_tuples'] > 0 and stats['live_tuples'] > 0:
            dead_ratio = (stats['dead_tuples'] / (stats['live_tuples'] + stats['dead_tuples'])) * 100
            self.log(f"  Dead tuple ratio: {dead_ratio:.2f}%")

        self.log(f"  Last VACUUM: {stats['last_vacuum'] or 'Never'}")
        self.log(f"  Last autovacuum: {stats['last_autovacuum'] or 'Never'}")
        self.log(f"  Last ANALYZE: {stats['last_analyze'] or 'Never'}")
        self.log(f"  Last autoanalyze: {stats['last_autoanalyze'] or 'Never'}")

    def vacuum_analyze_table(self, table_name, full=False, verbose=False):
        """
        Run VACUUM ANALYZE on specified table

        Args:
            table_name: Name of the table to vacuum
            full: If True, run VACUUM FULL (locks table, slower but reclaims more space)
            verbose: If True, run with VERBOSE option for detailed output

        Returns:
            bool: True if successful, False otherwise
        """
        # Check if table exists
        if not self.check_table_exists(table_name):
            self.log(f"❌ Table '{table_name}' does not exist")
            return False

        # Get activity statistics
        activity = self.get_database_activity()
        self.display_activity(activity)

        # Get table statistics before VACUUM
        stats_before = self.get_table_stats(table_name)
        if stats_before:
            self.display_table_stats(table_name, stats_before)
        else:
            self.log(f"⚠️  Could not retrieve statistics for table '{table_name}'")

        # Build VACUUM command
        vacuum_cmd = "VACUUM"
        if full:
            vacuum_cmd += " FULL"
            self.log("\n⚠️  Running VACUUM FULL - this will LOCK the table")
        if verbose:
            vacuum_cmd += " VERBOSE"
        vacuum_cmd += " ANALYZE"
        vacuum_cmd += f" {table_name}"

        self.log(f"\nExecuting: {vacuum_cmd}")

        try:
            start_time = time.time()
            self.cursor.execute(vacuum_cmd)
            elapsed = time.time() - start_time

            self.log(f"✅ VACUUM ANALYZE completed in {elapsed:.2f} seconds")

            # Get updated statistics
            stats_after = self.get_table_stats(table_name)
            if stats_after:
                self.log(f"\nUpdated Statistics:")
                self.log(f"  Dead tuples: {stats_before['dead_tuples']:,} → {stats_after['dead_tuples']:,}")
                if stats_before['dead_tuples'] > 0:
                    reclaimed = stats_before['dead_tuples'] - stats_after['dead_tuples']
                    self.log(f"  Reclaimed {reclaimed:,} dead tuples")

            return True

        except Exception as e:
            self.log(f"❌ VACUUM failed: {e}")
            return False

    def vacuum_all_tables(self, full=False, verbose=False):
        """
        Run VACUUM ANALYZE on all tables in the database

        Args:
            full: If True, run VACUUM FULL
            verbose: If True, run with VERBOSE option

        Returns:
            bool: True if successful, False otherwise
        """
        self.log("\nRetrieving all user tables...")

        self.cursor.execute("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)

        tables = [row[0] for row in self.cursor.fetchall()]
        self.log(f"Found {len(tables)} tables to vacuum")

        success_count = 0
        failed_count = 0

        for i, table in enumerate(tables, 1):
            self.log(f"\n{'='*70}")
            self.log(f"Table {i}/{len(tables)}: {table}")
            self.log('='*70)

            if self.vacuum_analyze_table(table, full=full, verbose=verbose):
                success_count += 1
            else:
                failed_count += 1

        # Summary
        self.log(f"\n{'='*70}")
        self.log(f"VACUUM COMPLETE")
        self.log(f"Successful: {success_count}/{len(tables)}")
        self.log(f"Failed: {failed_count}/{len(tables)}")
        self.log('='*70)

        return failed_count == 0

    def close(self):
        """Close database connection"""
        self.cursor.close()
        self.conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Run VACUUM ANALYZE on database tables',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Vacuum a specific table
  python vacuum_table.py --table authorship

  # Vacuum all tables
  python vacuum_table.py --all

  # Run VACUUM FULL (slower, locks table, but reclaims more space)
  python vacuum_table.py --table works --full

  # Run with verbose output
  python vacuum_table.py --table authors --verbose

  # Use test database
  python vacuum_table.py --table works --test
        """
    )

    parser.add_argument('--table', type=str, help='Specific table name to vacuum')
    parser.add_argument('--all', action='store_true', help='Vacuum all tables in database')
    parser.add_argument('--full', action='store_true', help='Run VACUUM FULL (locks table, reclaims more space)')
    parser.add_argument('--verbose', action='store_true', help='Run with VERBOSE output')
    parser.add_argument('--test', action='store_true', help='Use test database (oadbv5_test)')

    args = parser.parse_args()

    # Validate arguments
    if not args.table and not args.all:
        parser.error("Must specify either --table or --all")

    if args.table and args.all:
        parser.error("Cannot specify both --table and --all")

    manager = VacuumManager(test_mode=args.test)

    try:
        if args.all:
            success = manager.vacuum_all_tables(full=args.full, verbose=args.verbose)
        else:
            success = manager.vacuum_analyze_table(args.table, full=args.full, verbose=args.verbose)

        sys.exit(0 if success else 1)

    except Exception as e:
        manager.log(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        manager.close()

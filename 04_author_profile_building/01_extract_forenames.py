#!/usr/bin/env python3
"""
Extract author data from the OpenAlex database.

This script:
1. Connects to the PostgreSQL database (oadbv5)
2. Retrieves author_id, display_name, and current_affiliation_country from the authors table
3. Writes results to a DuckDB database in the datasets folder

The current_affiliation_country field contains the country code from the author's
most recent affiliation.
"""

import sys
from pathlib import Path
import logging
from datetime import datetime
import argparse
import duckdb

# Add parent directory to path for config imports
SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(PARENT_DIR))

import psycopg2
from config import DB_CONFIG


def setup_logging():
    """
    Setup logging to both console and file with proper formatting.

    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logs directory if it doesn't exist
    log_dir = SCRIPT_DIR / 'logs'
    log_dir.mkdir(exist_ok=True)

    # Create log file with timestamp
    log_file = log_dir / f'{Path(__file__).stem}_{datetime.now():%Y%m%d_%H%M%S}.log'

    # Configure logging to both file and console
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler()
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info(f"Starting {Path(__file__).name}")
    logger.info(f"Log file: {log_file}")

    return logger


def get_latest_country_query(limit=None):
    """
    Build the SQL query to extract authors with their latest country codes.

    The query:
    - Selects author_id, display_name, and current_affiliation_country
      directly from the authors table
    - The current_affiliation_country field already contains the country code
      from the author's most recent affiliation
    - Optionally limits the number of authors retrieved

    Args:
        limit (int, optional): Maximum number of authors to retrieve

    Returns:
        str: The SQL query string
    """
    query = """
    SELECT
        author_id,
        display_name,
        current_affiliation_country
    FROM authors
    """

    if limit:
        query += f"LIMIT {limit}"

    return query


def extract_authors_to_duckdb(limit=None, output_filename=None):
    """
    Extract author data with country codes and write to DuckDB.

    This function:
    1. Connects to the PostgreSQL database
    2. Executes the query to get authors with their latest country codes
    3. Writes results to a DuckDB database
    4. Provides progress updates during processing

    Args:
        limit (int, optional): Maximum number of authors to process
        output_filename (str, optional): Custom output filename

    Returns:
        tuple: (output_file_path, total_records_written)
    """
    logger = logging.getLogger(__name__)

    # Setup output file
    if output_filename is None:
        output_filename = 'author_data.duckdb'

    datasets_dir = SCRIPT_DIR / 'datasets'
    datasets_dir.mkdir(exist_ok=True)
    output_file = datasets_dir / output_filename

    logger.info(f"Output DuckDB file: {output_file}")

    # Connect to PostgreSQL database
    logger.info(f"Connecting to PostgreSQL: {DB_CONFIG['database']} at {DB_CONFIG['host']}:{DB_CONFIG['port']}")

    try:
        pg_conn = psycopg2.connect(**DB_CONFIG)
        pg_cursor = pg_conn.cursor()
        logger.info("PostgreSQL connection established")

        # Connect to DuckDB
        logger.info(f"Connecting to DuckDB: {output_file}")
        duck_conn = duckdb.connect(str(output_file))
        logger.info("DuckDB connection established")

        # Create table with author_id as primary key
        duck_conn.execute("""
            CREATE TABLE IF NOT EXISTS authors (
                author_id TEXT PRIMARY KEY,
                display_name TEXT,
                country_code TEXT
            )
        """)
        logger.info("DuckDB table created (or already exists)")

        # Clear existing data if table exists
        duck_conn.execute("DELETE FROM authors")
        logger.info("Cleared existing data from DuckDB table")

        # Execute PostgreSQL query
        query = get_latest_country_query(limit)
        logger.info(f"Executing query to extract author data (limit: {limit if limit else 'none'})")

        pg_cursor.execute(query)

        # Process results in batches for better performance
        batch_size = 10000
        total_written = 0
        start_time = datetime.now()

        logger.info("Starting to fetch and write records...")

        while True:
            rows = pg_cursor.fetchmany(batch_size)
            if not rows:
                break

            # Prepare batch data
            batch_data = []
            for row in rows:
                author_id, display_name, country_code = row
                batch_data.append((
                    author_id,
                    display_name if display_name else '',
                    country_code if country_code else ''
                ))

            # Insert batch into DuckDB
            duck_conn.executemany(
                "INSERT INTO authors (author_id, display_name, country_code) VALUES (?, ?, ?)",
                batch_data
            )

            total_written += len(batch_data)

            # Log progress
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = total_written / elapsed if elapsed > 0 else 0

            logger.info(
                f"Progress: {total_written:,} records written | "
                f"Rate: {rate:.0f} records/sec | "
                f"Elapsed: {elapsed:.0f}s"
            )

        # Close database connections
        pg_cursor.close()
        pg_conn.close()
        duck_conn.close()
        logger.info("Database connections closed")

        # Final statistics
        total_elapsed = (datetime.now() - start_time).total_seconds()
        avg_rate = total_written / total_elapsed if total_elapsed > 0 else 0

        logger.info("="*70)
        logger.info("EXTRACTION COMPLETE")
        logger.info("="*70)
        logger.info(f"Total records written: {total_written:,}")
        logger.info(f"Total time: {total_elapsed:.2f} seconds")
        logger.info(f"Average rate: {avg_rate:.0f} records/sec")
        logger.info(f"Output file: {output_file}")
        logger.info("="*70)

        return output_file, total_written

    except psycopg2.Error as e:
        logger.error(f"PostgreSQL error: {e}")
        raise
    except duckdb.Error as e:
        logger.error(f"DuckDB error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise


def main():
    """
    Main entry point for the script.

    Parses command line arguments and initiates the extraction process.
    """
    parser = argparse.ArgumentParser(
        description='Extract author data (author_id, display_name, country_code) from the OpenAlex database to DuckDB.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract first 1000 authors
  python 01_extract_forenames.py --limit 1000

  # Extract first 100k authors
  python 01_extract_forenames.py --limit 100000

  # Extract all authors (no limit)
  python 01_extract_forenames.py

  # Extract with custom output filename
  python 01_extract_forenames.py --limit 5000 --output test_author_data.duckdb
        """
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Maximum number of authors to extract (default: no limit, extract all authors)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Custom output filename (default: author_data.duckdb)'
    )

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging()

    logger.info("="*70)
    logger.info("AUTHOR DATA EXTRACTION TO DUCKDB")
    logger.info("="*70)
    logger.info(f"Limit: {args.limit if args.limit else 'None (all authors)'}")
    logger.info(f"Output filename: {args.output if args.output else 'author_data.duckdb'}")
    logger.info("="*70)

    try:
        # Run extraction
        output_file, total_records = extract_authors_to_duckdb(
            limit=args.limit,
            output_filename=args.output
        )

        logger.info("Script completed successfully")
        return 0

    except Exception as e:
        logger.critical(f"Script failed with error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())

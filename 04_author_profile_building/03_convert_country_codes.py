#!/usr/bin/env python3
"""
Convert country codes in DuckDB database to full country names.

This script:
1. Reads the author data from DuckDB database
2. Converts ISO 3166-1 alpha-2 country codes to full country names
3. Adds country_name column if it doesn't exist
4. Updates the database with converted country names

The country names are converted to formats compatible with genderComputer.
"""

import sys
from pathlib import Path
import logging
from datetime import datetime
import argparse
import duckdb

# Add current directory to path for imports
SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from country_code_mapping import get_country_name


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


def ensure_column_exists(conn):
    """
    Check if country_name column exists in the authors table and add it if not.

    Args:
        conn: DuckDB connection object

    Returns:
        None
    """
    logger = logging.getLogger(__name__)

    # Get current columns
    result = conn.execute("PRAGMA table_info(authors)").fetchall()
    existing_columns = {row[1] for row in result}  # row[1] is the column name

    logger.info(f"Existing columns: {existing_columns}")

    # Add country_name column if it doesn't exist
    if 'country_name' not in existing_columns:
        logger.info("Adding column: country_name (TEXT)")
        conn.execute("ALTER TABLE authors ADD COLUMN country_name TEXT")
    else:
        logger.info("Column already exists: country_name")


def convert_country_codes_in_duckdb(db_file):
    """
    Convert country codes in DuckDB database to full country names.

    This function:
    1. Connects to the DuckDB database
    2. Ensures country_name column exists
    3. Reads authors with country codes in batches of 50,000
    4. Converts country codes to full country names
    5. Updates the database with converted names
    6. Tracks conversion statistics

    Args:
        db_file (str or Path): Path to the DuckDB database file

    Returns:
        tuple: (total_records, converted_count, unconverted_count)
    """
    logger = logging.getLogger(__name__)

    db_file = Path(db_file)

    # Validate database file exists
    if not db_file.exists():
        raise FileNotFoundError(f"Database file not found: {db_file}")

    logger.info(f"Database file: {db_file}")

    # Connect to DuckDB
    conn = duckdb.connect(str(db_file))
    logger.info("DuckDB connection established")

    # Ensure country_name column exists
    logger.info("Checking for country_name column...")
    ensure_column_exists(conn)

    # Get total count of authors with country codes
    total_count = conn.execute(
        "SELECT COUNT(*) FROM authors WHERE country_code IS NOT NULL AND country_code != ''"
    ).fetchone()[0]
    logger.info(f"Total authors with country codes to process: {total_count:,}")

    # Statistics
    batch_size = 50000
    total_processed = 0
    converted_count = 0
    unconverted_count = 0
    unique_codes = set()
    unique_unconverted_codes = set()
    start_time = datetime.now()

    logger.info("Starting country code conversion...")

    # Process batches
    offset = 0
    while offset < total_count:
        # Fetch batch - only rows with country codes
        batch = conn.execute(
            f"""SELECT author_id, country_code FROM authors
                WHERE country_code IS NOT NULL AND country_code != ''
                LIMIT {batch_size} OFFSET {offset}"""
        ).fetchall()

        if not batch:
            break

        # Prepare updates
        updates = []
        for author_id, country_code in batch:
            # Track unique country codes (all rows have codes due to WHERE clause)
            unique_codes.add(country_code)

            # Convert country code to country name
            country_name = get_country_name(country_code)
            if country_name:
                converted_count += 1
            else:
                unconverted_count += 1
                unique_unconverted_codes.add(country_code)
                country_name = ''

            updates.append((country_name, author_id))

        # Perform batch update
        conn.executemany(
            """
            UPDATE authors
            SET country_name = ?
            WHERE author_id = ?
            """,
            updates
        )

        total_processed += len(batch)
        offset += batch_size

        # Log progress
        elapsed = (datetime.now() - start_time).total_seconds()
        rate = total_processed / elapsed if elapsed > 0 else 0
        pct_complete = (total_processed / total_count * 100) if total_count > 0 else 0

        logger.info(
            f"Progress: {total_processed:,}/{total_count:,} ({pct_complete:.1f}%) | "
            f"Rate: {rate:.0f} records/sec | "
            f"Converted: {converted_count:,} | "
            f"Unconverted: {unconverted_count:,}"
        )

    # Close connection
    conn.close()
    logger.info("DuckDB connection closed")

    # Final statistics
    total_elapsed = (datetime.now() - start_time).total_seconds()
    avg_rate = total_processed / total_elapsed if total_elapsed > 0 else 0

    logger.info("="*70)
    logger.info("COUNTRY CODE CONVERSION COMPLETE")
    logger.info("="*70)
    logger.info(f"Total records processed: {total_processed:,}")
    logger.info(f"Successfully converted: {converted_count:,} ({converted_count/total_processed*100:.2f}%)" if total_processed > 0 else "N/A")
    logger.info(f"Could not convert: {unconverted_count:,} ({unconverted_count/total_processed*100:.2f}%)" if total_processed > 0 else "N/A")
    logger.info(f"Unique country codes found: {len(unique_codes)}")
    logger.info(f"Unique codes that couldn't be converted: {len(unique_unconverted_codes)}")
    if unique_unconverted_codes:
        logger.info(f"Unconverted codes: {sorted(unique_unconverted_codes)}")
    logger.info(f"Total time: {total_elapsed:.2f} seconds")
    logger.info(f"Average rate: {avg_rate:.0f} records/sec")
    logger.info("="*70)

    return total_processed, converted_count, unconverted_count


def main():
    """
    Main entry point for the script.

    Parses command line arguments and initiates the country code conversion.
    """
    # Default database path (same as created by 01_extract_forenames.py)
    default_db_path = SCRIPT_DIR / 'datasets' / 'author_data.duckdb'

    parser = argparse.ArgumentParser(
        description='Convert ISO country codes to full country names in DuckDB database.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert country codes in default database
  python 03_convert_country_codes.py

  # Convert with custom database file
  python 03_convert_country_codes.py --db datasets/my_authors.duckdb
        """
    )

    parser.add_argument(
        '--db',
        type=str,
        default=str(default_db_path),
        help=f'Path to the DuckDB database file containing author data (default: {default_db_path})'
    )

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging()

    logger.info("="*70)
    logger.info("COUNTRY CODE CONVERSION IN DUCKDB")
    logger.info("="*70)
    logger.info(f"Database file: {args.db}")
    logger.info("="*70)

    try:
        # Run conversion
        total_records, converted, unconverted = convert_country_codes_in_duckdb(
            db_file=args.db
        )

        logger.info("Script completed successfully")
        return 0

    except FileNotFoundError as e:
        logger.error(f"File error: {e}")
        return 1
    except duckdb.Error as e:
        logger.error(f"DuckDB error: {e}")
        return 1
    except Exception as e:
        logger.critical(f"Script failed with error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())

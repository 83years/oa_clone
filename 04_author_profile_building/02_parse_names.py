#!/usr/bin/env python3
"""
Parse author names to extract forenames and surnames using python-nameparser.

This script:
1. Reads the author data from DuckDB database
2. Uses the nameparser library to parse display names
3. Extracts forenames (first names) and surnames (last names)
4. Identifies initials and marks them as "no_forename" gender
5. Writes results back to the same DuckDB database

The nameparser library handles various name formats including:
- Simple names (John Smith)
- Names with middle names (John Michael Smith)
- Names with titles (Dr. John Smith)
- Names with suffixes (John Smith Jr.)
- International name formats
"""

import sys
from pathlib import Path
import logging
from datetime import datetime
import argparse
import re
import duckdb
from nameparser import HumanName

# Add parent directory to path for config imports
SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(PARENT_DIR))


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


def is_initial(name_part):
    """
    Check if a name part is an initial.

    An initial is defined as:
    - A single letter (with or without a period)
    - Multiple single letters separated by spaces or periods (e.g., "J. K.")

    Args:
        name_part (str): The name part to check

    Returns:
        bool: True if the name part is an initial, False otherwise
    """
    if not name_part:
        return False

    # Remove periods and spaces
    cleaned = name_part.replace('.', '').replace(' ', '')

    # Check if it's only letters and is 1-2 characters (common for initials like "J" or "JK")
    # Most real names are longer than 2 characters
    if cleaned.isalpha() and len(cleaned) <= 2:
        return True

    return False


def parse_author_name(display_name):
    """
    Parse an author's display name to extract forename, surname, and detect initials.

    Uses the HumanName class from the nameparser library to intelligently
    parse names in various formats. Also detects if the forename is an initial.

    Args:
        display_name (str): The full display name of the author

    Returns:
        tuple: (forename, surname, has_initial)
            - forename: First name (may include middle names)
            - surname: Last name (family name)
            - has_initial: Boolean indicating if forename is an initial
    """
    if not display_name:
        return ('', '', False)

    try:
        # Parse the name using HumanName
        name = HumanName(display_name)

        # Extract forename (first name) and surname (last name)
        forename = name.first
        surname = name.last

        # Check if forename is an initial
        has_initial = is_initial(forename)

        return (forename, surname, has_initial)

    except Exception as e:
        # If parsing fails for any reason, return empty strings
        return ('', '', False)


def ensure_columns_exist(conn):
    """
    Check if required columns exist in the authors table and add them if not.

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

    # Define columns we need
    required_columns = {
        'forename': 'TEXT',
        'surname': 'TEXT',
        'gender': 'TEXT'
    }

    # Add missing columns
    for column_name, column_type in required_columns.items():
        if column_name not in existing_columns:
            logger.info(f"Adding column: {column_name} ({column_type})")
            conn.execute(f"ALTER TABLE authors ADD COLUMN {column_name} {column_type}")
        else:
            logger.info(f"Column already exists: {column_name}")


def parse_names_in_duckdb(db_file):
    """
    Parse author names from DuckDB database and update with forename/surname/gender.

    This function:
    1. Connects to the DuckDB database
    2. Ensures required columns exist (forename, surname, gender)
    3. Reads authors in batches of 50,000
    4. Parses each author's display name
    5. Extracts forename and surname
    6. Marks authors with initials as "no_forename" gender
    7. Updates the database with parsed results
    8. Provides progress updates during processing

    Args:
        db_file (str or Path): Path to the DuckDB database file

    Returns:
        tuple: (total_records_processed, records_with_initials, failed_parses)
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

    # Ensure required columns exist
    logger.info("Checking for required columns...")
    ensure_columns_exist(conn)

    # Get total count of authors
    total_count = conn.execute("SELECT COUNT(*) FROM authors").fetchone()[0]
    logger.info(f"Total authors to process: {total_count:,}")

    # Process in batches
    batch_size = 50000
    total_processed = 0
    records_with_initials = 0
    failed_parses = 0
    start_time = datetime.now()

    logger.info("Starting name parsing...")

    # Process batches
    offset = 0
    while offset < total_count:
        # Fetch batch
        batch = conn.execute(
            f"SELECT author_id, display_name FROM authors LIMIT {batch_size} OFFSET {offset}"
        ).fetchall()

        if not batch:
            break

        # Prepare updates
        updates = []
        for author_id, display_name in batch:
            # Parse the name
            forename, surname, has_initial = parse_author_name(display_name)

            # Determine gender based on initials
            gender = 'no_forename' if has_initial else None

            # Track statistics
            if display_name and not forename and not surname:
                failed_parses += 1

            if has_initial:
                records_with_initials += 1

            updates.append((forename, surname, gender, author_id))

        # Perform batch update
        conn.executemany(
            """
            UPDATE authors
            SET forename = ?, surname = ?, gender = ?
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
            f"Elapsed: {elapsed:.0f}s | "
            f"With initials: {records_with_initials:,} | "
            f"Failed: {failed_parses:,}"
        )

    # Close connection
    conn.close()
    logger.info("DuckDB connection closed")

    # Final statistics
    total_elapsed = (datetime.now() - start_time).total_seconds()
    avg_rate = total_processed / total_elapsed if total_elapsed > 0 else 0

    logger.info("="*70)
    logger.info("NAME PARSING COMPLETE")
    logger.info("="*70)
    logger.info(f"Total records processed: {total_processed:,}")
    logger.info(f"Records with initials (no_forename gender): {records_with_initials:,} ({records_with_initials/total_processed*100:.2f}%)")
    logger.info(f"Failed parses: {failed_parses:,} ({failed_parses/total_processed*100:.2f}%)" if total_processed > 0 else "N/A")
    logger.info(f"Successful parses: {total_processed - failed_parses:,}")
    logger.info(f"Total time: {total_elapsed:.2f} seconds")
    logger.info(f"Average rate: {avg_rate:.0f} records/sec")
    logger.info("="*70)

    return total_processed, records_with_initials, failed_parses


def main():
    """
    Main entry point for the script.

    Parses command line arguments and initiates the name parsing process.
    """
    # Default database path (same as created by 01_extract_forenames.py)
    default_db_path = SCRIPT_DIR / 'datasets' / 'author_data.duckdb'

    parser = argparse.ArgumentParser(
        description='Parse author names from DuckDB database to extract forenames and surnames.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Parse names from the default database file
  python 02_parse_names.py

  # Parse with custom database file
  python 02_parse_names.py --db datasets/my_authors.duckdb
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
    logger.info("AUTHOR NAME PARSING FROM DUCKDB")
    logger.info("="*70)
    logger.info(f"Database file: {args.db}")
    logger.info("="*70)

    try:
        # Run name parsing
        total_records, records_with_initials, failed_parses = parse_names_in_duckdb(
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

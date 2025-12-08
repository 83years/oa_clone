#!/usr/bin/env python3
"""
Infer author gender using genderComputer.

This script:
1. Reads author data from DuckDB database
2. Uses genderComputer to infer gender based on forename and country
3. Adds gendercomputer_gender column to the database
4. Updates the database with inferred gender

The genderComputer package analyzes first names and country information
to predict gender. Returns 'male', 'female', or None (uncertain).
"""

import sys
from pathlib import Path
import logging
from datetime import datetime
import argparse
import duckdb

# Add parent directory to path for genderComputer import
SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
GENDERCOMPUTER_DIR = PARENT_DIR / 'genderComputer'
sys.path.insert(0, str(GENDERCOMPUTER_DIR))

from genderComputer.genderComputer import GenderComputer


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
    Check if gendercomputer_gender column exists in the authors table and add it if not.

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

    # Add gendercomputer_gender column if it doesn't exist
    if 'gendercomputer_gender' not in existing_columns:
        logger.info("Adding column: gendercomputer_gender (TEXT)")
        conn.execute("ALTER TABLE authors ADD COLUMN gendercomputer_gender TEXT")
    else:
        logger.info("Column already exists: gendercomputer_gender")


def infer_gender_in_duckdb(db_file):
    """
    Infer gender for authors in DuckDB database using genderComputer.

    This function:
    1. Connects to the DuckDB database
    2. Ensures gendercomputer_gender column exists
    3. Initializes genderComputer
    4. Reads authors in batches (only those without 'no_forename' in gender field)
    5. Infers gender for each author based on forename and country
    6. Updates the database with inferred gender
    7. Tracks inference statistics

    Args:
        db_file (str or Path): Path to the DuckDB database file

    Returns:
        tuple: (total_records, male_count, female_count, unknown_count)
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

    # Ensure gendercomputer_gender column exists
    logger.info("Checking for gendercomputer_gender column...")
    ensure_column_exists(conn)

    # Initialize genderComputer
    logger.info("Initializing genderComputer...")
    gc = GenderComputer()
    logger.info("genderComputer initialized successfully")

    # Get count of authors to process (exclude those already marked as 'no_forename' in gender field)
    count_query = """
        SELECT COUNT(*) FROM authors
        WHERE gender IS NULL OR gender != 'no_forename'
    """
    total_count = conn.execute(count_query).fetchone()[0]
    logger.info(f"Total authors to process: {total_count:,}")

    # Statistics
    batch_size = 10000  # Smaller batches since genderComputer may be slower
    total_processed = 0
    male_count = 0
    female_count = 0
    unknown_count = 0
    with_country_count = 0
    without_country_count = 0
    start_time = datetime.now()

    logger.info("Starting gender inference...")

    # Process batches
    offset = 0
    while offset < total_count:
        # Fetch batch (only authors without 'no_forename' in gender field)
        fetch_query = """
            SELECT author_id, forename, country_name
            FROM authors
            WHERE gender IS NULL OR gender != 'no_forename'
            LIMIT ? OFFSET ?
        """
        batch = conn.execute(fetch_query, [batch_size, offset]).fetchall()

        if not batch:
            break

        # Prepare updates
        updates = []
        for author_id, forename, country_name in batch:
            # Track country availability
            if country_name:
                with_country_count += 1
            else:
                without_country_count += 1

            # Infer gender using genderComputer
            try:
                gender = gc.resolveGender(forename, country_name if country_name else None)
            except Exception as e:
                logger.warning(f"Error inferring gender for '{forename}' ({country_name}): {e}")
                gender = None

            # Update statistics
            if gender == 'male':
                male_count += 1
            elif gender == 'female':
                female_count += 1
            else:
                unknown_count += 1

            # Store the result (empty string if None)
            gender_value = gender if gender else ''
            updates.append((gender_value, author_id))

        # Perform batch update
        conn.executemany(
            """
            UPDATE authors
            SET gendercomputer_gender = ?
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
            f"Male: {male_count:,} | Female: {female_count:,} | Unknown: {unknown_count:,}"
        )

    # Close connection
    conn.close()
    logger.info("DuckDB connection closed")

    # Final statistics
    total_elapsed = (datetime.now() - start_time).total_seconds()
    avg_rate = total_processed / total_elapsed if total_elapsed > 0 else 0
    success_rate = ((male_count + female_count) / total_processed * 100) if total_processed > 0 else 0

    logger.info("="*70)
    logger.info("GENDER INFERENCE COMPLETE")
    logger.info("="*70)
    logger.info(f"Total records processed: {total_processed:,}")
    logger.info(f"Records with country: {with_country_count:,} ({with_country_count/total_processed*100:.2f}%)" if total_processed > 0 else "N/A")
    logger.info(f"Records without country: {without_country_count:,} ({without_country_count/total_processed*100:.2f}%)" if total_processed > 0 else "N/A")
    logger.info("")
    logger.info("Gender Distribution:")
    logger.info(f"  Male: {male_count:,} ({male_count/total_processed*100:.2f}%)" if total_processed > 0 else "N/A")
    logger.info(f"  Female: {female_count:,} ({female_count/total_processed*100:.2f}%)" if total_processed > 0 else "N/A")
    logger.info(f"  Unknown: {unknown_count:,} ({unknown_count/total_processed*100:.2f}%)" if total_processed > 0 else "N/A")
    logger.info(f"  Success rate: {success_rate:.2f}%")
    logger.info("")
    logger.info(f"Total time: {total_elapsed:.2f} seconds")
    logger.info(f"Average rate: {avg_rate:.0f} records/sec")
    logger.info("="*70)

    return total_processed, male_count, female_count, unknown_count


def main():
    """
    Main entry point for the script.

    Parses command line arguments and initiates the gender inference process.
    """
    # Default database path (same as created by 01_extract_forenames.py)
    default_db_path = SCRIPT_DIR / 'datasets' / 'author_data.duckdb'

    parser = argparse.ArgumentParser(
        description='Infer author gender using genderComputer based on forename and country.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Infer gender from default database
  python 05_infer_genderComputer.py

  # Infer gender with custom database file
  python 05_infer_genderComputer.py --db datasets/my_authors.duckdb

Gender inference:
  - Uses forename and country_name to predict gender
  - Returns: 'male', 'female', or empty (unknown)
  - Country information improves accuracy for ambiguous names
  - Skips authors already marked as 'no_forename' in the gender field (initials)
  - Results stored in gendercomputer_gender column
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
    logger.info("AUTHOR GENDER INFERENCE WITH GENDERCOMPUTER")
    logger.info("="*70)
    logger.info(f"Database file: {args.db}")
    logger.info("="*70)

    try:
        # Run gender inference
        total_records, male, female, unknown = infer_gender_in_duckdb(
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

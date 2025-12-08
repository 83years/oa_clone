#!/usr/bin/env python3
"""
Infer author gender using local names database.

This script:
1. Reads author data from DuckDB database
2. Matches forenames against the local_names.db database
3. Adds local_gender column to the database
4. Updates the database with matched gender from local database

The local_names.db database contains ~31 million forenames with gender information.
Matches are performed on lowercase forename against the 'name' column.
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
    Check if local_gender column exists in the authors table and add it if not.

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

    # Add local_gender column if it doesn't exist
    if 'local_gender' not in existing_columns:
        logger.info("Adding column: local_gender (TEXT)")
        conn.execute("ALTER TABLE authors ADD COLUMN local_gender TEXT")
    else:
        logger.info("Column already exists: local_gender")


def infer_gender_in_duckdb(db_file, local_names_db):
    """
    Infer gender for authors in DuckDB database using local names database.

    This function:
    1. Connects to both DuckDB databases (authors and local_names)
    2. Ensures local_gender column exists
    3. Reads authors in batches (only those without 'no_forename' in gender field)
    4. Matches forenames against local_names.db
    5. Updates the database with matched gender
    6. Tracks matching statistics

    Args:
        db_file (str or Path): Path to the authors DuckDB database file
        local_names_db (str or Path): Path to the local_names.db database file

    Returns:
        tuple: (total_records, matched_count, unmatched_count, gender_stats)
    """
    logger = logging.getLogger(__name__)

    db_file = Path(db_file)
    local_names_db = Path(local_names_db)

    # Validate database files exist
    if not db_file.exists():
        raise FileNotFoundError(f"Authors database file not found: {db_file}")
    if not local_names_db.exists():
        raise FileNotFoundError(f"Local names database file not found: {local_names_db}")

    logger.info(f"Authors database: {db_file}")
    logger.info(f"Local names database: {local_names_db}")

    # Connect to authors DuckDB
    conn = duckdb.connect(str(db_file))
    logger.info("Authors DuckDB connection established")

    # Attach local names database as a separate database
    logger.info("Attaching local names database...")
    conn.execute(f"ATTACH '{local_names_db}' AS local_db (READ_ONLY)")
    logger.info("Local names database attached successfully")

    # Check local database structure
    local_count = conn.execute("SELECT COUNT(*) FROM local_db.forenames").fetchone()[0]
    logger.info(f"Local names database contains {local_count:,} forenames")

    # Ensure local_gender column exists
    logger.info("Checking for local_gender column...")
    ensure_column_exists(conn)

    # Get count of authors to process (exclude those already marked as 'no_forename' in gender field)
    count_query = """
        SELECT COUNT(*) FROM authors
        WHERE gender IS NULL OR gender != 'no_forename'
    """
    total_count = conn.execute(count_query).fetchone()[0]
    logger.info(f"Total authors to process: {total_count:,}")

    # Statistics
    batch_size = 50000  # Larger batches since lookup should be fast
    total_processed = 0
    matched_count = 0
    unmatched_count = 0
    gender_stats = {
        'm': 0,
        'f': 0,
        'male': 0,
        'female': 0,
        'unknown': 0,
        'other': 0
    }
    start_time = datetime.now()

    logger.info("Starting gender inference from local database...")

    # Process batches
    offset = 0
    while offset < total_count:
        # Fetch batch (only authors without 'no_forename' in gender field)
        fetch_query = """
            SELECT author_id, forename
            FROM authors
            WHERE gender IS NULL OR gender != 'no_forename'
            LIMIT ? OFFSET ?
        """
        batch = conn.execute(fetch_query, [batch_size, offset]).fetchall()

        if not batch:
            break

        # Prepare updates by looking up each forename in local database
        updates = []
        for author_id, forename in batch:
            if not forename:
                gender_result = None
                unmatched_count += 1
            else:
                # Convert forename to lowercase for matching (local db stores names in lowercase)
                forename_lower = forename.lower().strip()

                # Look up in local database
                # Note: We're not using the countries column as instructed
                # Order by frequency to get the most common gender for this name
                lookup_query = """
                    SELECT gender
                    FROM local_db.forenames
                    WHERE name = ?
                    ORDER BY frequency DESC
                    LIMIT 1
                """
                result = conn.execute(lookup_query, [forename_lower]).fetchone()

                if result:
                    gender_result = result[0]
                    matched_count += 1
                else:
                    gender_result = None
                    unmatched_count += 1

            # Update statistics
            if gender_result in gender_stats:
                gender_stats[gender_result] += 1
            elif gender_result:
                # Track any unexpected gender values
                gender_stats['other'] += 1

            # Store the result (empty string if None)
            gender_value = gender_result if gender_result else ''
            updates.append((gender_value, author_id))

        # Perform batch update
        conn.executemany(
            """
            UPDATE authors
            SET local_gender = ?
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
            f"Matched: {matched_count:,} | Unmatched: {unmatched_count:,}"
        )

    # Detach local database
    conn.execute("DETACH local_db")

    # Close connection
    conn.close()
    logger.info("DuckDB connections closed")

    # Final statistics
    total_elapsed = (datetime.now() - start_time).total_seconds()
    avg_rate = total_processed / total_elapsed if total_elapsed > 0 else 0
    match_rate = (matched_count / total_processed * 100) if total_processed > 0 else 0

    # Calculate combined male/female counts for summary
    total_male = gender_stats['m'] + gender_stats['male']
    total_female = gender_stats['f'] + gender_stats['female']

    logger.info("="*70)
    logger.info("GENDER INFERENCE COMPLETE")
    logger.info("="*70)
    logger.info(f"Total records processed: {total_processed:,}")
    logger.info(f"Successfully matched: {matched_count:,} ({match_rate:.2f}%)")
    logger.info(f"Unmatched: {unmatched_count:,} ({unmatched_count/total_processed*100:.2f}%)" if total_processed > 0 else "N/A")
    logger.info("")
    logger.info("Gender Distribution (matched only):")
    if matched_count > 0:
        logger.info(f"  Male (combined): {total_male:,} ({total_male/matched_count*100:.2f}%)")
        logger.info(f"    - 'm': {gender_stats['m']:,}")
        logger.info(f"    - 'male': {gender_stats['male']:,}")
        logger.info(f"  Female (combined): {total_female:,} ({total_female/matched_count*100:.2f}%)")
        logger.info(f"    - 'f': {gender_stats['f']:,}")
        logger.info(f"    - 'female': {gender_stats['female']:,}")
        logger.info(f"  Unknown: {gender_stats['unknown']:,} ({gender_stats['unknown']/matched_count*100:.2f}%)")
        if gender_stats['other'] > 0:
            logger.info(f"  Other: {gender_stats['other']:,} ({gender_stats['other']/matched_count*100:.2f}%)")
    else:
        logger.info("  No matches found")
    logger.info("")
    logger.info(f"Total time: {total_elapsed:.2f} seconds")
    logger.info(f"Average rate: {avg_rate:.0f} records/sec")
    logger.info("="*70)

    return total_processed, matched_count, unmatched_count, gender_stats


def main():
    """
    Main entry point for the script.

    Parses command line arguments and initiates the gender inference process.
    """
    # Default database paths
    default_db_path = SCRIPT_DIR / 'datasets' / 'author_data.duckdb'
    default_local_names_db = SCRIPT_DIR / 'datasets' / 'local_names.db'

    parser = argparse.ArgumentParser(
        description='Infer author gender using local names database.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Infer gender from default databases
  python 07_infer_genderLocal.py

  # Infer gender with custom database files
  python 07_infer_genderLocal.py --db datasets/my_authors.duckdb --local-db datasets/my_local_names.db

Gender inference:
  - Matches forename (lowercase) against local_names.db 'name' column
  - Returns: 'm' (male), 'f' (female), or empty (no match)
  - Does NOT use the countries column (as instructed)
  - Skips authors already marked as 'no_forename' in the gender field (initials)
  - Results stored in local_gender column
  - Local database contains ~31 million forenames
        """
    )

    parser.add_argument(
        '--db',
        type=str,
        default=str(default_db_path),
        help=f'Path to the DuckDB database file containing author data (default: {default_db_path})'
    )

    parser.add_argument(
        '--local-db',
        type=str,
        default=str(default_local_names_db),
        help=f'Path to the local_names.db database file (default: {default_local_names_db})'
    )

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging()

    logger.info("="*70)
    logger.info("AUTHOR GENDER INFERENCE WITH LOCAL DATABASE")
    logger.info("="*70)
    logger.info(f"Authors database: {args.db}")
    logger.info(f"Local names database: {args.local_db}")
    logger.info("="*70)

    try:
        # Run gender inference
        total_records, matched, unmatched, gender_stats = infer_gender_in_duckdb(
            db_file=args.db,
            local_names_db=args.local_db
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

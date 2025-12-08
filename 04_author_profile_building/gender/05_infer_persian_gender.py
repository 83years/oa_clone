#!/usr/bin/env python3
"""
Infer author gender using persian-gender-detection (optimized for Persian/Iranian names).

This script:
1. Reads author data from DuckDB database
2. Uses persian-gender-detection to infer gender based on forename
3. Adds persian_gender column to the database
4. Updates the database with inferred gender

The persian-gender-detection package uses a database of 19K+ Persian names.
Returns 'MALE', 'FEMALE', or 'UNKNOWN'.
"""

import sys
from pathlib import Path
import logging
from datetime import datetime
import argparse
import duckdb

SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(PARENT_DIR))

try:
    from persian_gender_detection import get_gender, get_gender_nearest
    PERSIAN_GENDER_AVAILABLE = True
except ImportError:
    PERSIAN_GENDER_AVAILABLE = False
    print("WARNING: persian-gender-detection not installed. Install with: pip install persian-gender-detection")


def setup_logging():
    """
    Setup logging to both console and file with proper formatting.

    Returns:
        logging.Logger: Configured logger instance
    """
    log_dir = SCRIPT_DIR / 'logs'
    log_dir.mkdir(exist_ok=True)

    log_file = log_dir / f'{Path(__file__).stem}_{datetime.now():%Y%m%d_%H%M%S}.log'

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
    Check if persian_gender column exists in the authors table and add it if not.

    Args:
        conn: DuckDB connection object

    Returns:
        None
    """
    logger = logging.getLogger(__name__)

    result = conn.execute("PRAGMA table_info(authors)").fetchall()
    existing_columns = {row[1] for row in result}

    logger.info(f"Existing columns: {existing_columns}")

    if 'persian_gender' not in existing_columns:
        logger.info("Adding column: persian_gender (TEXT)")
        conn.execute("ALTER TABLE authors ADD COLUMN persian_gender TEXT")
    else:
        logger.info("Column already exists: persian_gender")


def infer_gender_in_duckdb(db_file, country_filter=None, use_nearest=True):
    """
    Infer gender for authors in DuckDB database using persian-gender-detection.

    This function:
    1. Connects to the DuckDB database
    2. Ensures persian_gender column exists
    3. Reads authors in batches (optionally filtered by country)
    4. Infers gender for each author based on forename
    5. Uses get_gender_nearest for better matching if enabled
    6. Updates the database with inferred gender
    7. Tracks inference statistics

    Args:
        db_file (str or Path): Path to the DuckDB database file
        country_filter (str, optional): If provided, only process authors from this country (e.g., 'Iran')
        use_nearest (bool): If True, use get_gender_nearest for better matching (default: True)

    Returns:
        tuple: (total_records, male_count, female_count, unknown_count)
    """
    logger = logging.getLogger(__name__)

    db_file = Path(db_file)

    if not db_file.exists():
        raise FileNotFoundError(f"Database file not found: {db_file}")

    logger.info(f"Database file: {db_file}")

    conn = duckdb.connect(str(db_file))
    logger.info("DuckDB connection established")

    logger.info("Checking for persian_gender column...")
    ensure_column_exists(conn)

    logger.info("Initializing persian-gender-detection...")
    if not PERSIAN_GENDER_AVAILABLE:
        raise ImportError("persian-gender-detection package not available. Install with: pip install persian-gender-detection")
    logger.info(f"persian-gender-detection initialized successfully (use_nearest={use_nearest})")

    if country_filter:
        count_query = """
            SELECT COUNT(*) FROM authors
            WHERE (gender IS NULL OR gender != 'no_forename')
            AND country_name = ?
        """
        total_count = conn.execute(count_query, [country_filter]).fetchone()[0]
        logger.info(f"Total authors to process (filtered by {country_filter}): {total_count:,}")
    else:
        count_query = """
            SELECT COUNT(*) FROM authors
            WHERE gender IS NULL OR gender != 'no_forename'
        """
        total_count = conn.execute(count_query).fetchone()[0]
        logger.info(f"Total authors to process: {total_count:,}")

    batch_size = 10000
    total_processed = 0
    male_count = 0
    female_count = 0
    unknown_count = 0
    iran_count = 0
    non_iran_count = 0
    nearest_used_count = 0
    start_time = datetime.now()

    logger.info("Starting gender inference...")

    offset = 0
    while offset < total_count:
        if country_filter:
            fetch_query = """
                SELECT author_id, forename, country_name
                FROM authors
                WHERE (gender IS NULL OR gender != 'no_forename')
                AND country_name = ?
                LIMIT ? OFFSET ?
            """
            batch = conn.execute(fetch_query, [country_filter, batch_size, offset]).fetchall()
        else:
            fetch_query = """
                SELECT author_id, forename, country_name
                FROM authors
                WHERE gender IS NULL OR gender != 'no_forename'
                LIMIT ? OFFSET ?
            """
            batch = conn.execute(fetch_query, [batch_size, offset]).fetchall()

        if not batch:
            break

        updates = []
        for author_id, forename, country_name in batch:
            if country_name and country_name.lower() == 'iran':
                iran_count += 1
            else:
                non_iran_count += 1

            try:
                gender = get_gender(forename)

                if gender == 'UNKNOWN' and use_nearest:
                    try:
                        result = get_gender_nearest(forename)
                        if isinstance(result, tuple) and len(result) == 2:
                            gender, matched_name = result
                            if gender != 'UNKNOWN':
                                nearest_used_count += 1
                    except Exception:
                        pass

            except Exception as e:
                logger.warning(f"Error inferring gender for '{forename}': {e}")
                gender = 'UNKNOWN'

            if gender == 'MALE':
                male_count += 1
                gender_value = 'male'
            elif gender == 'FEMALE':
                female_count += 1
                gender_value = 'female'
            else:
                unknown_count += 1
                gender_value = 'unknown'

            updates.append((gender_value, author_id))

        conn.executemany(
            """
            UPDATE authors
            SET persian_gender = ?
            WHERE author_id = ?
            """,
            updates
        )

        total_processed += len(batch)
        offset += batch_size

        elapsed = (datetime.now() - start_time).total_seconds()
        rate = total_processed / elapsed if elapsed > 0 else 0
        pct_complete = (total_processed / total_count * 100) if total_count > 0 else 0

        logger.info(
            f"Progress: {total_processed:,}/{total_count:,} ({pct_complete:.1f}%) | "
            f"Rate: {rate:.0f} records/sec | "
            f"Male: {male_count:,} | Female: {female_count:,} | Unknown: {unknown_count:,}"
        )

    conn.close()
    logger.info("DuckDB connection closed")

    total_elapsed = (datetime.now() - start_time).total_seconds()
    avg_rate = total_processed / total_elapsed if total_elapsed > 0 else 0
    success_rate = ((male_count + female_count) / total_processed * 100) if total_processed > 0 else 0

    logger.info("="*70)
    logger.info("PERSIAN GENDER DETECTION COMPLETE")
    logger.info("="*70)
    logger.info(f"Total records processed: {total_processed:,}")
    logger.info(f"Records from Iran: {iran_count:,} ({iran_count/total_processed*100:.2f}%)" if total_processed > 0 else "N/A")
    logger.info(f"Records from other countries: {non_iran_count:,} ({non_iran_count/total_processed*100:.2f}%)" if total_processed > 0 else "N/A")
    if use_nearest:
        logger.info(f"Nearest match used: {nearest_used_count:,} times")
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
    default_db_path = SCRIPT_DIR / 'datasets' / 'author_data.duckdb'

    parser = argparse.ArgumentParser(
        description='Infer author gender using persian-gender-detection (optimized for Persian names).',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Infer gender from default database
  python 13_infer_persian_gender.py

  # Process only Iranian authors
  python 13_infer_persian_gender.py --country Iran

  # Disable nearest matching (exact match only)
  python 13_infer_persian_gender.py --no-nearest

  # Infer gender with custom database file
  python 13_infer_persian_gender.py --db datasets/my_authors.duckdb

Gender inference:
  - Uses database of 19K+ Persian names
  - Returns: 'male', 'female', or 'unknown'
  - Best results for Persian/Farsi names
  - get_gender_nearest handles multi-part names and spelling variations
  - Results stored in persian_gender column
        """
    )

    parser.add_argument(
        '--db',
        type=str,
        default=str(default_db_path),
        help=f'Path to the DuckDB database file containing author data (default: {default_db_path})'
    )

    parser.add_argument(
        '--country',
        type=str,
        default=None,
        help='Filter by country name (e.g., "Iran") to process only authors from that country'
    )

    parser.add_argument(
        '--no-nearest',
        action='store_true',
        help='Disable nearest matching (use exact match only)'
    )

    args = parser.parse_args()

    logger = setup_logging()

    logger.info("="*70)
    logger.info("AUTHOR GENDER INFERENCE WITH PERSIAN-GENDER-DETECTION")
    logger.info("="*70)
    logger.info(f"Database file: {args.db}")
    if args.country:
        logger.info(f"Country filter: {args.country}")
    logger.info(f"Nearest matching: {'disabled' if args.no_nearest else 'enabled'}")
    logger.info("="*70)

    try:
        total_records, male, female, unknown = infer_gender_in_duckdb(
            db_file=args.db,
            country_filter=args.country,
            use_nearest=not args.no_nearest
        )

        logger.info("Script completed successfully")
        return 0

    except FileNotFoundError as e:
        logger.error(f"File error: {e}")
        return 1
    except ImportError as e:
        logger.error(f"Import error: {e}")
        return 1
    except duckdb.Error as e:
        logger.error(f"DuckDB error: {e}")
        return 1
    except Exception as e:
        logger.critical(f"Script failed with error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())

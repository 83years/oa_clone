#!/usr/bin/env python3
"""
Infer author gender using gender-guesser.

This script:
1. Reads author data from DuckDB database
2. Uses gender-guesser to infer gender based on forename and country
3. Adds genderguesser_gender column to the database
4. Updates the database with inferred gender

The gender-guesser package analyzes first names and country information
to predict gender. Returns 'male', 'female', 'mostly_male', 'mostly_female',
'andy' (androgynous), or 'unknown'.
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

import gender_guesser.detector as gender


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
    Check if genderguesser_gender column exists in the authors table and add it if not.

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

    # Add genderguesser_gender column if it doesn't exist
    if 'genderguesser_gender' not in existing_columns:
        logger.info("Adding column: genderguesser_gender (TEXT)")
        conn.execute("ALTER TABLE authors ADD COLUMN genderguesser_gender TEXT")
    else:
        logger.info("Column already exists: genderguesser_gender")


def convert_country_name_to_code(country_name):
    """
    Convert full country name to country code for gender-guesser.

    gender-guesser expects lowercase country names like 'usa', 'italy', 'britain'.
    This function converts common country names to the format expected by gender-guesser.

    Args:
        country_name (str): Full country name

    Returns:
        str or None: Country code/name in format expected by gender-guesser
    """
    if not country_name:
        return None

    # Convert to lowercase for matching
    country_lower = country_name.lower().strip()

    # Common mappings (gender-guesser uses specific country names)
    country_mapping = {
        'united states': 'usa',
        'united states of america': 'usa',
        'united kingdom': 'britain',
        'great britain': 'britain',
        'england': 'britain',
        'scotland': 'britain',
        'wales': 'britain',
    }

    # Check if we have a specific mapping
    if country_lower in country_mapping:
        return country_mapping[country_lower]

    # Otherwise return the country name as-is (lowercase)
    # gender-guesser will use it if it recognizes it
    return country_lower


def infer_gender_in_duckdb(db_file):
    """
    Infer gender for authors in DuckDB database using gender-guesser.

    This function:
    1. Connects to the DuckDB database
    2. Ensures genderguesser_gender column exists
    3. Initializes gender-guesser Detector
    4. Reads authors in batches (only those without 'no_forename' in gender field)
    5. Infers gender for each author based on forename and country
    6. Updates the database with inferred gender
    7. Tracks inference statistics

    Args:
        db_file (str or Path): Path to the DuckDB database file

    Returns:
        tuple: (total_records, stats_dict)
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

    # Ensure genderguesser_gender column exists
    logger.info("Checking for genderguesser_gender column...")
    ensure_column_exists(conn)

    # Initialize gender-guesser
    logger.info("Initializing gender-guesser Detector...")
    detector = gender.Detector()
    logger.info("gender-guesser Detector initialized successfully")

    # Get count of authors to process (exclude those already marked as 'no_forename' in gender field)
    count_query = """
        SELECT COUNT(*) FROM authors
        WHERE gender IS NULL OR gender != 'no_forename'
    """
    total_count = conn.execute(count_query).fetchone()[0]
    logger.info(f"Total authors to process: {total_count:,}")

    # Statistics
    batch_size = 10000
    total_processed = 0
    gender_stats = {
        'male': 0,
        'female': 0,
        'mostly_male': 0,
        'mostly_female': 0,
        'andy': 0,  # androgynous
        'unknown': 0
    }
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

            # Convert country name to format expected by gender-guesser
            country_code = convert_country_name_to_code(country_name)

            # Infer gender using gender-guesser
            try:
                inferred_gender = detector.get_gender(forename, country_code)
            except Exception as e:
                logger.warning(f"Error inferring gender for '{forename}' ({country_name}): {e}")
                inferred_gender = 'unknown'

            # Update statistics
            if inferred_gender in gender_stats:
                gender_stats[inferred_gender] += 1
            else:
                gender_stats['unknown'] += 1
                inferred_gender = 'unknown'

            # Store the result
            updates.append((inferred_gender, author_id))

        # Perform batch update
        conn.executemany(
            """
            UPDATE authors
            SET genderguesser_gender = ?
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
            f"Male: {gender_stats['male']:,} | Female: {gender_stats['female']:,} | "
            f"Unknown: {gender_stats['unknown']:,}"
        )

    # Close connection
    conn.close()
    logger.info("DuckDB connection closed")

    # Final statistics
    total_elapsed = (datetime.now() - start_time).total_seconds()
    avg_rate = total_processed / total_elapsed if total_elapsed > 0 else 0
    definite_count = gender_stats['male'] + gender_stats['female']
    success_rate = (definite_count / total_processed * 100) if total_processed > 0 else 0

    logger.info("="*70)
    logger.info("GENDER INFERENCE COMPLETE")
    logger.info("="*70)
    logger.info(f"Total records processed: {total_processed:,}")
    logger.info(f"Records with country: {with_country_count:,} ({with_country_count/total_processed*100:.2f}%)" if total_processed > 0 else "N/A")
    logger.info(f"Records without country: {without_country_count:,} ({without_country_count/total_processed*100:.2f}%)" if total_processed > 0 else "N/A")
    logger.info("")
    logger.info("Gender Distribution:")
    logger.info(f"  Male: {gender_stats['male']:,} ({gender_stats['male']/total_processed*100:.2f}%)" if total_processed > 0 else "N/A")
    logger.info(f"  Female: {gender_stats['female']:,} ({gender_stats['female']/total_processed*100:.2f}%)" if total_processed > 0 else "N/A")
    logger.info(f"  Mostly Male: {gender_stats['mostly_male']:,} ({gender_stats['mostly_male']/total_processed*100:.2f}%)" if total_processed > 0 else "N/A")
    logger.info(f"  Mostly Female: {gender_stats['mostly_female']:,} ({gender_stats['mostly_female']/total_processed*100:.2f}%)" if total_processed > 0 else "N/A")
    logger.info(f"  Androgynous: {gender_stats['andy']:,} ({gender_stats['andy']/total_processed*100:.2f}%)" if total_processed > 0 else "N/A")
    logger.info(f"  Unknown: {gender_stats['unknown']:,} ({gender_stats['unknown']/total_processed*100:.2f}%)" if total_processed > 0 else "N/A")
    logger.info(f"  Definite success rate (male/female only): {success_rate:.2f}%")
    logger.info("")
    logger.info(f"Total time: {total_elapsed:.2f} seconds")
    logger.info(f"Average rate: {avg_rate:.0f} records/sec")
    logger.info("="*70)

    return total_processed, gender_stats


def main():
    """
    Main entry point for the script.

    Parses command line arguments and initiates the gender inference process.
    """
    # Default database path (same as created by 01_extract_forenames.py)
    default_db_path = SCRIPT_DIR / 'datasets' / 'author_data.duckdb'

    parser = argparse.ArgumentParser(
        description='Infer author gender using gender-guesser based on forename and country.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Infer gender from default database
  python 06_infer_genderGuesser.py

  # Infer gender with custom database file
  python 06_infer_genderGuesser.py --db datasets/my_authors.duckdb

Gender inference:
  - Uses forename and country_name to predict gender
  - Returns: 'male', 'female', 'mostly_male', 'mostly_female', 'andy' (androgynous), or 'unknown'
  - Country information improves accuracy for ambiguous names
  - Skips authors already marked as 'no_forename' in the gender field (initials)
  - Results stored in genderguesser_gender column
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
    logger.info("AUTHOR GENDER INFERENCE WITH GENDER-GUESSER")
    logger.info("="*70)
    logger.info(f"Database file: {args.db}")
    logger.info("="*70)

    try:
        # Run gender inference
        total_records, gender_stats = infer_gender_in_duckdb(
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

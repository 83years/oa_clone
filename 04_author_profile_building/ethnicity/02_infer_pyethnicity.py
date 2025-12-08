#!/usr/bin/env python3
"""
Infer author race using pyethnicity.

This script:
1. Reads author data from DuckDB database
2. Uses pyethnicity to infer race/ethnicity based on first and last name
3. Adds pyethnicity_* columns to the database for race probabilities
4. Updates the database with inferred race probabilities

pyethnicity predicts 4 US-centric race categories with probabilities:
- asian
- black
- hispanic
- white

This tool uses advanced ML models trained on Florida voter registration data
and outperforms most existing open-source ethnicity prediction models.
"""

import sys
from pathlib import Path
import logging
from datetime import datetime
import argparse
import duckdb

# Import pyethnicity
try:
    import pyethnicity as pe
    PYETHNICITY_AVAILABLE = True
except ImportError:
    PYETHNICITY_AVAILABLE = False
    print("ERROR: pyethnicity not installed. Install with: pip install pyethnicity")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent


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


def ensure_columns_exist(conn):
    """
    Check if pyethnicity columns exist in the authors table and add them if not.

    Args:
        conn: DuckDB connection object

    Returns:
        None
    """
    logger = logging.getLogger(__name__)

    result = conn.execute("PRAGMA table_info(authors)").fetchall()
    existing_columns = {row[1] for row in result}

    columns_to_add = {
        'pyethnicity_asian': 'DOUBLE',
        'pyethnicity_black': 'DOUBLE',
        'pyethnicity_hispanic': 'DOUBLE',
        'pyethnicity_white': 'DOUBLE'
    }

    for col_name, col_type in columns_to_add.items():
        if col_name not in existing_columns:
            logger.info(f"Adding column: {col_name} ({col_type})")
            conn.execute(f"ALTER TABLE authors ADD COLUMN {col_name} {col_type}")
        else:
            logger.info(f"Column already exists: {col_name}")


def infer_ethnicity_in_duckdb(db_file, batch_size=100):
    """
    Infer race/ethnicity for authors in DuckDB database using pyethnicity.

    This function:
    1. Connects to the DuckDB database
    2. Ensures pyethnicity columns exist
    3. Reads authors in batches
    4. Infers race probabilities for each author
    5. Updates the database with probability scores
    6. Tracks inference statistics

    Args:
        db_file (Path): Path to DuckDB database file
        batch_size (int): Number of records to process in each batch (default: 100)
                         Note: Smaller batch size due to ML model overhead

    Returns:
        None
    """
    logger = logging.getLogger(__name__)

    logger.info("="*70)
    logger.info("RACE/ETHNICITY INFERENCE USING PYETHNICITY")
    logger.info("="*70)
    logger.info(f"Database: {db_file}")
    logger.info(f"Batch size: {batch_size:,}")
    logger.info("="*70)

    # Connect to DuckDB database
    conn = duckdb.connect(str(db_file))

    # Ensure columns exist
    ensure_columns_exist(conn)

    # Get total count of authors to process
    total_count = conn.execute("""
        SELECT COUNT(*)
        FROM authors
        WHERE forename IS NOT NULL AND forename != ''
        AND surname IS NOT NULL AND surname != ''
    """).fetchone()[0]

    logger.info(f"Total authors to process: {total_count:,}")
    logger.info("="*70)

    if total_count == 0:
        logger.warning("No authors found with both forename and surname")
        conn.close()
        return

    # Statistics tracking
    total_processed = 0
    race_counts = {'asian': 0, 'black': 0, 'hispanic': 0, 'white': 0}
    start_time = datetime.now()

    # Process in batches
    for offset in range(0, total_count, batch_size):
        # Fetch batch of authors
        batch_query = f"""
            SELECT author_id, forename, surname
            FROM authors
            WHERE forename IS NOT NULL AND forename != ''
            AND surname IS NOT NULL AND surname != ''
            ORDER BY author_id
            LIMIT {batch_size} OFFSET {offset}
        """

        batch_results = conn.execute(batch_query).fetchall()

        if not batch_results:
            break

        # Process each name in batch (pyethnicity processes one at a time)
        updates = []

        for author_id, forename, surname in batch_results:
            try:
                # Predict race using Florida voter model
                result_df = pe.predict_race_fl(forename, surname)

                # Extract probabilities from polars DataFrame
                asian_prob = float(result_df['asian'][0])
                black_prob = float(result_df['black'][0])
                hispanic_prob = float(result_df['hispanic'][0])
                white_prob = float(result_df['white'][0])

                # Determine primary race (highest probability)
                probs = {
                    'asian': asian_prob,
                    'black': black_prob,
                    'hispanic': hispanic_prob,
                    'white': white_prob
                }
                primary_race = max(probs, key=probs.get)
                race_counts[primary_race] += 1

                updates.append((asian_prob, black_prob, hispanic_prob, white_prob, author_id))

            except Exception as e:
                logger.warning(f"Error processing {forename} {surname}: {e}")
                # Add null values for failed predictions
                updates.append((None, None, None, None, author_id))
                continue

        # Bulk update
        if updates:
            conn.executemany("""
                UPDATE authors
                SET pyethnicity_asian = ?,
                    pyethnicity_black = ?,
                    pyethnicity_hispanic = ?,
                    pyethnicity_white = ?
                WHERE author_id = ?
            """, updates)

        total_processed += len(batch_results)

        # Progress logging
        elapsed = (datetime.now() - start_time).total_seconds()
        rate = total_processed / elapsed if elapsed > 0 else 0
        pct_complete = (total_processed / total_count * 100) if total_count > 0 else 0

        logger.info(
            f"Progress: {total_processed:,}/{total_count:,} ({pct_complete:.1f}%) | "
            f"Rate: {rate:.1f} records/sec | "
            f"Elapsed: {elapsed:.0f}s"
        )

    # Close connection
    conn.close()

    # Final statistics
    total_elapsed = (datetime.now() - start_time).total_seconds()
    avg_rate = total_processed / total_elapsed if total_elapsed > 0 else 0

    logger.info("="*70)
    logger.info("PYETHNICITY INFERENCE COMPLETE")
    logger.info("="*70)
    logger.info(f"Total records processed: {total_processed:,}")
    logger.info("")
    logger.info("Primary Race Distribution (by highest probability):")
    for race in sorted(race_counts.keys()):
        count = race_counts[race]
        pct = (count / total_processed * 100) if total_processed > 0 else 0
        logger.info(f"  {race}: {count:,} ({pct:.2f}%)")
    logger.info("")
    logger.info(f"Total time: {total_elapsed:.2f} seconds")
    logger.info(f"Average rate: {avg_rate:.1f} records/sec")
    logger.info("="*70)


def main():
    """
    Main function to run race/ethnicity inference using pyethnicity.

    Parses command-line arguments and initiates the inference process.
    """
    default_db_path = SCRIPT_DIR / 'datasets' / 'author_data.duckdb'

    parser = argparse.ArgumentParser(
        description='Infer author race/ethnicity using pyethnicity.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default database
  python 02_infer_pyethnicity.py

  # Run with custom database
  python 02_infer_pyethnicity.py --db datasets/my_authors.duckdb

  # Use custom batch size
  python 02_infer_pyethnicity.py --batch-size 50

About pyethnicity:
  pyethnicity predicts race using advanced ML models trained on
  Florida voter registration data. It outputs probabilities for:
  - Asian
  - Black
  - Hispanic
  - White

  The model is optimized for US names but can work with international names.
  Note: Processing is slower than other tools due to ML model overhead.
        """
    )

    parser.add_argument(
        '--db',
        type=str,
        default=str(default_db_path),
        help=f'Path to the DuckDB database file (default: {default_db_path})'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Number of records to process in each batch (default: 100)'
    )

    args = parser.parse_args()

    logger = setup_logging()

    db_path = Path(args.db)

    if not db_path.exists():
        logger.error(f"Database file not found: {db_path}")
        return 1

    try:
        infer_ethnicity_in_duckdb(db_path, batch_size=args.batch_size)
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())

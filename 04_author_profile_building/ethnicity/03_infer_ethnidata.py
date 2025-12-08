#!/usr/bin/env python3
"""
Infer author nationality/ethnicity using ethnidata.

This script:
1. Reads author data from DuckDB database
2. Uses ethnidata to infer nationality based on first and last name
3. Adds ethnidata_* columns to the database
4. Updates the database with inferred nationality, region, language, and confidence

ethnidata predicts:
- Country/Nationality (238 countries)
- Region (6 major regions: Africa, Americas, Asia, Europe, Oceania, Middle East)
- Language (72 languages)
- Confidence score

ethnidata uses a database of 169,197 first names and 246,537 last names
to provide nationality predictions with regional and linguistic context.
"""

import sys
from pathlib import Path
import logging
from datetime import datetime
import argparse
import duckdb

# Import ethnidata
try:
    from ethnidata import EthniData
    ETHNIDATA_AVAILABLE = True
except ImportError:
    ETHNIDATA_AVAILABLE = False
    print("ERROR: ethnidata not installed. Install with: pip install ethnidata")
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
    Check if ethnidata columns exist in the authors table and add them if not.

    Args:
        conn: DuckDB connection object

    Returns:
        None
    """
    logger = logging.getLogger(__name__)

    result = conn.execute("PRAGMA table_info(authors)").fetchall()
    existing_columns = {row[1] for row in result}

    columns_to_add = {
        'ethnidata_country_code': 'TEXT',
        'ethnidata_country_name': 'TEXT',
        'ethnidata_region': 'TEXT',
        'ethnidata_language': 'TEXT',
        'ethnidata_confidence': 'DOUBLE'
    }

    for col_name, col_type in columns_to_add.items():
        if col_name not in existing_columns:
            logger.info(f"Adding column: {col_name} ({col_type})")
            conn.execute(f"ALTER TABLE authors ADD COLUMN {col_name} {col_type}")
        else:
            logger.info(f"Column already exists: {col_name}")


def infer_ethnicity_in_duckdb(db_file, batch_size=1000):
    """
    Infer nationality/ethnicity for authors in DuckDB database using ethnidata.

    This function:
    1. Connects to the DuckDB database
    2. Ensures ethnidata columns exist
    3. Initializes ethnidata predictor
    4. Reads authors in batches
    5. Infers nationality, region, and language for each author
    6. Updates the database with prediction results
    7. Tracks inference statistics

    Args:
        db_file (Path): Path to DuckDB database file
        batch_size (int): Number of records to process in each batch (default: 1000)

    Returns:
        None
    """
    logger = logging.getLogger(__name__)

    logger.info("="*70)
    logger.info("NATIONALITY/ETHNICITY INFERENCE USING ETHNIDATA")
    logger.info("="*70)
    logger.info(f"Database: {db_file}")
    logger.info(f"Batch size: {batch_size:,}")
    logger.info("="*70)

    # Connect to DuckDB database
    conn = duckdb.connect(str(db_file))

    # Ensure columns exist
    ensure_columns_exist(conn)

    # Initialize ethnidata
    logger.info("Initializing ethnidata predictor...")
    try:
        predictor = EthniData()
        stats = predictor.get_stats()
        logger.info(f"Ethnidata database loaded:")
        logger.info(f"  - {stats['total_first_names']:,} first names")
        logger.info(f"  - {stats['total_last_names']:,} last names")
        logger.info(f"  - {stats['countries']} countries")
        logger.info(f"  - {stats['regions']} regions")
        logger.info(f"  - {stats['languages']} languages")
    except Exception as e:
        logger.error(f"Failed to initialize ethnidata: {e}")
        conn.close()
        return

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
    region_counts = {}
    country_counts = {}
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

        # Process each name
        updates = []

        for author_id, forename, surname in batch_results:
            try:
                # Predict using full name
                result = predictor.predict_full_name(forename, surname, top_n=1)

                country_code = result.get('country')
                country_name = result.get('country_name')
                region = result.get('region')
                language = result.get('language')
                confidence = result.get('confidence', 0.0)

                # Track statistics
                if region:
                    region_counts[region] = region_counts.get(region, 0) + 1
                if country_name:
                    country_counts[country_name] = country_counts.get(country_name, 0) + 1

                updates.append((
                    country_code,
                    country_name,
                    region,
                    language,
                    confidence,
                    author_id
                ))

            except Exception as e:
                logger.warning(f"Error processing {forename} {surname}: {e}")
                # Add null values for failed predictions
                updates.append((None, None, None, None, None, author_id))
                continue

        # Bulk update
        if updates:
            conn.executemany("""
                UPDATE authors
                SET ethnidata_country_code = ?,
                    ethnidata_country_name = ?,
                    ethnidata_region = ?,
                    ethnidata_language = ?,
                    ethnidata_confidence = ?
                WHERE author_id = ?
            """, updates)

        total_processed += len(batch_results)

        # Progress logging
        elapsed = (datetime.now() - start_time).total_seconds()
        rate = total_processed / elapsed if elapsed > 0 else 0
        pct_complete = (total_processed / total_count * 100) if total_count > 0 else 0

        logger.info(
            f"Progress: {total_processed:,}/{total_count:,} ({pct_complete:.1f}%) | "
            f"Rate: {rate:.0f} records/sec | "
            f"Elapsed: {elapsed:.0f}s"
        )

    # Close connection
    conn.close()

    # Final statistics
    total_elapsed = (datetime.now() - start_time).total_seconds()
    avg_rate = total_processed / total_elapsed if total_elapsed > 0 else 0

    logger.info("="*70)
    logger.info("ETHNIDATA INFERENCE COMPLETE")
    logger.info("="*70)
    logger.info(f"Total records processed: {total_processed:,}")
    logger.info("")
    logger.info("Regional Distribution:")
    for region in sorted(region_counts.keys()):
        count = region_counts[region]
        pct = (count / total_processed * 100) if total_processed > 0 else 0
        logger.info(f"  {region}: {count:,} ({pct:.2f}%)")
    logger.info("")
    logger.info("Top 10 Countries:")
    top_countries = sorted(country_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    for country, count in top_countries:
        pct = (count / total_processed * 100) if total_processed > 0 else 0
        logger.info(f"  {country}: {count:,} ({pct:.2f}%)")
    logger.info("")
    logger.info(f"Total time: {total_elapsed:.2f} seconds")
    logger.info(f"Average rate: {avg_rate:.0f} records/sec")
    logger.info("="*70)


def main():
    """
    Main function to run nationality/ethnicity inference using ethnidata.

    Parses command-line arguments and initiates the inference process.
    """
    default_db_path = SCRIPT_DIR / 'datasets' / 'author_data.duckdb'

    parser = argparse.ArgumentParser(
        description='Infer author nationality/ethnicity using ethnidata.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default database
  python 03_infer_ethnidata.py

  # Run with custom database
  python 03_infer_ethnidata.py --db datasets/my_authors.duckdb

  # Use custom batch size
  python 03_infer_ethnidata.py --batch-size 5000

About ethnidata:
  ethnidata predicts nationality/ethnicity with:
  - Country prediction (238 countries)
  - Regional classification (6 major regions)
  - Language identification (72 languages)
  - Confidence scores

  The database contains:
  - 169,197 first names
  - 246,537 last names

  This provides more granular nationality predictions compared to
  broader ethnic categories from other tools.
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
        default=1000,
        help='Number of records to process in each batch (default: 1000)'
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

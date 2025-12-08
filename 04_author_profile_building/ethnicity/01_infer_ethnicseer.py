#!/usr/bin/env python3
"""
Infer author ethnicity using ethnicseer.

This script:
1. Reads author data from DuckDB database
2. Uses ethnicseer to infer ethnicity based on full name
3. Adds ethnicseer_ethnicity and ethnicseer_confidence columns to the database
4. Updates the database with inferred ethnicity

ethnicseer predicts 12 ethnic categories:
- chi (Chinese)
- eng (English)
- frn (French)
- ger (German)
- ind (Indian)
- ita (Italian)
- jap (Japanese)
- kor (Korean)
- mea (Middle-Eastern)
- rus (Russian)
- spa (Spanish)
- vie (Vietnamese)

Achieves approximately 84% accuracy on test data.
"""

import sys
from pathlib import Path
import logging
from datetime import datetime
import argparse
import duckdb

# Import ethnicseer
try:
    from ethnicseer import EthnicClassifier
    ETHNICSEER_AVAILABLE = True
except ImportError:
    ETHNICSEER_AVAILABLE = False
    print("ERROR: ethnicseer not installed. Install with: pip install ethnicseer")
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
    Check if ethnicseer columns exist in the authors table and add them if not.

    Args:
        conn: DuckDB connection object

    Returns:
        None
    """
    logger = logging.getLogger(__name__)

    result = conn.execute("PRAGMA table_info(authors)").fetchall()
    existing_columns = {row[1] for row in result}

    if 'ethnicseer_ethnicity' not in existing_columns:
        logger.info("Adding column: ethnicseer_ethnicity (TEXT)")
        conn.execute("ALTER TABLE authors ADD COLUMN ethnicseer_ethnicity TEXT")
    else:
        logger.info("Column already exists: ethnicseer_ethnicity")

    if 'ethnicseer_confidence' not in existing_columns:
        logger.info("Adding column: ethnicseer_confidence (DOUBLE)")
        conn.execute("ALTER TABLE authors ADD COLUMN ethnicseer_confidence DOUBLE")
    else:
        logger.info("Column already exists: ethnicseer_confidence")


def infer_ethnicity_in_duckdb(db_file, batch_size=1000):
    """
    Infer ethnicity for authors in DuckDB database using ethnicseer.

    This function:
    1. Connects to the DuckDB database
    2. Ensures ethnicseer columns exist
    3. Initializes ethnicseer classifier
    4. Reads authors in batches
    5. Infers ethnicity for each author based on display_name
    6. Updates the database with inferred ethnicity and confidence scores
    7. Tracks inference statistics

    Args:
        db_file (Path): Path to DuckDB database file
        batch_size (int): Number of records to process in each batch (default: 1000)

    Returns:
        None
    """
    logger = logging.getLogger(__name__)

    logger.info("="*70)
    logger.info("ETHNICITY INFERENCE USING ETHNICSEER")
    logger.info("="*70)
    logger.info(f"Database: {db_file}")
    logger.info(f"Batch size: {batch_size:,}")
    logger.info("="*70)

    # Connect to DuckDB database
    conn = duckdb.connect(str(db_file))

    # Ensure columns exist
    ensure_columns_exist(conn)

    # Initialize ethnicseer
    logger.info("Loading ethnicseer pre-trained model...")
    try:
        classifier = EthnicClassifier.load_pretrained_model()
        ethnicities = classifier.ethnicity_classes()
        logger.info(f"Model loaded. Supported ethnicities: {', '.join(ethnicities)}")
    except Exception as e:
        logger.error(f"Failed to load ethnicseer model: {e}")
        conn.close()
        return

    # Get total count of authors to process
    total_count = conn.execute("""
        SELECT COUNT(*)
        FROM authors
        WHERE display_name IS NOT NULL AND display_name != ''
    """).fetchone()[0]

    logger.info(f"Total authors to process: {total_count:,}")
    logger.info("="*70)

    if total_count == 0:
        logger.warning("No authors found to process")
        conn.close()
        return

    # Statistics tracking
    total_processed = 0
    ethnicity_counts = {eth: 0 for eth in ethnicities}
    start_time = datetime.now()

    # Process in batches
    for offset in range(0, total_count, batch_size):
        # Fetch batch of authors
        batch_query = f"""
            SELECT author_id, display_name
            FROM authors
            WHERE display_name IS NOT NULL AND display_name != ''
            ORDER BY author_id
            LIMIT {batch_size} OFFSET {offset}
        """

        batch_results = conn.execute(batch_query).fetchall()

        if not batch_results:
            break

        # Prepare names for batch prediction
        names = [row[1] for row in batch_results]

        # Get predictions with scores
        try:
            ethnicities_pred, confidences = classifier.classify_names_with_scores(names)

            # Prepare updates
            updates = []
            for i, (author_id, _) in enumerate(batch_results):
                ethnicity = ethnicities_pred[i] if i < len(ethnicities_pred) else None
                confidence = float(confidences[i]) if i < len(confidences) else 0.0

                if ethnicity:
                    ethnicity_counts[ethnicity] = ethnicity_counts.get(ethnicity, 0) + 1

                updates.append((ethnicity, confidence, author_id))

            # Bulk update
            conn.executemany("""
                UPDATE authors
                SET ethnicseer_ethnicity = ?,
                    ethnicseer_confidence = ?
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

        except Exception as e:
            logger.error(f"Error processing batch at offset {offset}: {e}")
            continue

    # Close connection
    conn.close()

    # Final statistics
    total_elapsed = (datetime.now() - start_time).total_seconds()
    avg_rate = total_processed / total_elapsed if total_elapsed > 0 else 0

    logger.info("="*70)
    logger.info("ETHNICSEER INFERENCE COMPLETE")
    logger.info("="*70)
    logger.info(f"Total records processed: {total_processed:,}")
    logger.info("")
    logger.info("Ethnicity Distribution:")
    for ethnicity in sorted(ethnicity_counts.keys()):
        count = ethnicity_counts[ethnicity]
        if count > 0:
            pct = (count / total_processed * 100) if total_processed > 0 else 0
            logger.info(f"  {ethnicity}: {count:,} ({pct:.2f}%)")
    logger.info("")
    logger.info(f"Total time: {total_elapsed:.2f} seconds")
    logger.info(f"Average rate: {avg_rate:.0f} records/sec")
    logger.info("="*70)


def main():
    """
    Main function to run ethnicity inference using ethnicseer.

    Parses command-line arguments and initiates the inference process.
    """
    default_db_path = SCRIPT_DIR / 'datasets' / 'author_data.duckdb'

    parser = argparse.ArgumentParser(
        description='Infer author ethnicity using ethnicseer.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default database
  python 01_infer_ethnicseer.py

  # Run with custom database
  python 01_infer_ethnicseer.py --db datasets/my_authors.duckdb

  # Use custom batch size
  python 01_infer_ethnicseer.py --batch-size 5000

About ethnicseer:
  ethnicseer predicts 12 ethnic categories based on name analysis:
  Chinese, English, French, German, Indian, Italian, Japanese, Korean,
  Middle-Eastern, Russian, Spanish, Vietnamese

  The pre-trained model achieves approximately 84% accuracy.
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

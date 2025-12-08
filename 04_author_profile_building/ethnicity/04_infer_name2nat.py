#!/usr/bin/env python3
"""
Infer author nationality using name2nat.

This script:
1. Reads author data from DuckDB database
2. Uses name2nat to infer nationality based on full name
3. Adds name2nat_* columns to the database
4. Updates the database with inferred nationality predictions (top 3)

name2nat predicts 254 nationalities from Wikipedia data:
- Covers global nationalities from Afghan to Yemeni
- Uses bidirectional GRU neural network (Flair NLP)
- Trained on 1.1 million names from Wikipedia (June 2020)

Accuracy:
- Top-1: 55.1%
- Top-3: 77.9%
- Top-5: 86.8%

Note: This tool may have dependency conflicts in some environments.
If installation fails, you can skip this tool and use the other tools in the pipeline.
"""

import sys
from pathlib import Path
import logging
from datetime import datetime
import argparse
import duckdb

# Check for name2nat availability
try:
    from name2nat import Name2nat
    NAME2NAT_AVAILABLE = True
except ImportError as e:
    NAME2NAT_AVAILABLE = False
    print("="*70)
    print("WARNING: name2nat not available")
    print("="*70)
    print(f"Error: {e}")
    print()
    print("name2nat has dependency conflicts in some environments.")
    print("To install, try:")
    print("  pip install name2nat")
    print()
    print("If installation fails, you can skip this tool.")
    print("The ethnicity pipeline will work with the other tools.")
    print("="*70)

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
    Check if name2nat columns exist in the authors table and add them if not.

    Args:
        conn: DuckDB connection object

    Returns:
        None
    """
    logger = logging.getLogger(__name__)

    result = conn.execute("PRAGMA table_info(authors)").fetchall()
    existing_columns = {row[1] for row in result}

    columns_to_add = {
        'name2nat_nationality1': 'TEXT',
        'name2nat_probability1': 'DOUBLE',
        'name2nat_nationality2': 'TEXT',
        'name2nat_probability2': 'DOUBLE',
        'name2nat_nationality3': 'TEXT',
        'name2nat_probability3': 'DOUBLE'
    }

    for col_name, col_type in columns_to_add.items():
        if col_name not in existing_columns:
            logger.info(f"Adding column: {col_name} ({col_type})")
            conn.execute(f"ALTER TABLE authors ADD COLUMN {col_name} {col_type}")
        else:
            logger.info(f"Column already exists: {col_name}")


def infer_nationality_in_duckdb(db_file, batch_size=100):
    """
    Infer nationality for authors in DuckDB database using name2nat.

    This function:
    1. Connects to the DuckDB database
    2. Ensures name2nat columns exist
    3. Initializes name2nat classifier
    4. Reads authors in batches
    5. Infers nationality for each author based on full name
    6. Stores top 3 predictions with probabilities
    7. Tracks inference statistics

    Args:
        db_file (Path): Path to DuckDB database file
        batch_size (int): Number of records to process in each batch (default: 100)

    Returns:
        None
    """
    logger = logging.getLogger(__name__)

    if not NAME2NAT_AVAILABLE:
        logger.error("name2nat is not available. Cannot proceed.")
        logger.error("Install with: pip install name2nat")
        return

    logger.info("="*70)
    logger.info("NATIONALITY INFERENCE USING NAME2NAT")
    logger.info("="*70)
    logger.info(f"Database: {db_file}")
    logger.info(f"Batch size: {batch_size:,}")
    logger.info("="*70)

    # Connect to DuckDB database
    conn = duckdb.connect(str(db_file))

    # Ensure columns exist
    ensure_columns_exist(conn)

    # Initialize name2nat
    logger.info("Loading name2nat model (this may take a moment)...")
    try:
        classifier = Name2nat()
        logger.info("name2nat model loaded successfully")
    except Exception as e:
        logger.error(f"Failed to load name2nat model: {e}")
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
        logger.warning("No authors found with display names")
        conn.close()
        return

    # Statistics tracking
    total_processed = 0
    nationality_counts = {}
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
        author_ids = [row[0] for row in batch_results]
        names = [row[1] for row in batch_results]

        try:
            # Get predictions with top 3 results
            predictions = classifier(names, top_n=3)

            # Prepare updates
            updates = []

            for i, (author_id, pred_list) in enumerate(zip(author_ids, predictions)):
                # pred_list is like [('American', 0.95), ('English', 0.03), ...]
                nat1, prob1 = pred_list[0] if len(pred_list) > 0 else (None, None)
                nat2, prob2 = pred_list[1] if len(pred_list) > 1 else (None, None)
                nat3, prob3 = pred_list[2] if len(pred_list) > 2 else (None, None)

                # Track top nationality
                if nat1:
                    nationality_counts[nat1] = nationality_counts.get(nat1, 0) + 1

                updates.append((nat1, prob1, nat2, prob2, nat3, prob3, author_id))

            # Bulk update
            conn.executemany("""
                UPDATE authors
                SET name2nat_nationality1 = ?,
                    name2nat_probability1 = ?,
                    name2nat_nationality2 = ?,
                    name2nat_probability2 = ?,
                    name2nat_nationality3 = ?,
                    name2nat_probability3 = ?
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

        except Exception as e:
            logger.error(f"Error processing batch at offset {offset}: {e}")
            continue

    # Close connection
    conn.close()

    # Final statistics
    total_elapsed = (datetime.now() - start_time).total_seconds()
    avg_rate = total_processed / total_elapsed if total_elapsed > 0 else 0

    logger.info("="*70)
    logger.info("NAME2NAT INFERENCE COMPLETE")
    logger.info("="*70)
    logger.info(f"Total records processed: {total_processed:,}")
    logger.info("")
    logger.info("Top 10 Nationalities (by top-1 prediction):")
    top_nationalities = sorted(nationality_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    for nationality, count in top_nationalities:
        pct = (count / total_processed * 100) if total_processed > 0 else 0
        logger.info(f"  {nationality}: {count:,} ({pct:.2f}%)")
    logger.info("")
    logger.info(f"Total time: {total_elapsed:.2f} seconds")
    logger.info(f"Average rate: {avg_rate:.1f} records/sec")
    logger.info("="*70)


def main():
    """
    Main function to run nationality inference using name2nat.

    Parses command-line arguments and initiates the inference process.
    """
    if not NAME2NAT_AVAILABLE:
        print("ERROR: name2nat is not available. Exiting.")
        return 1

    default_db_path = SCRIPT_DIR / 'datasets' / 'author_data.duckdb'

    parser = argparse.ArgumentParser(
        description='Infer author nationality using name2nat.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default database
  python 04_infer_name2nat.py

  # Run with custom database
  python 04_infer_name2nat.py --db datasets/my_authors.duckdb

  # Use custom batch size
  python 04_infer_name2nat.py --batch-size 50

About name2nat:
  name2nat predicts 254 nationalities using a bidirectional GRU neural network
  trained on 1.1 million names from Wikipedia (June 2020 dump).

  Accuracy:
  - Top-1: 55.1%
  - Top-3: 77.9%
  - Top-5: 86.8%

  This tool provides highly granular nationality predictions covering
  Afghan to Yemeni and everything in between.

  Note: Processing may be slower than other tools due to neural network overhead.
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
        infer_nationality_in_duckdb(db_path, batch_size=args.batch_size)
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())

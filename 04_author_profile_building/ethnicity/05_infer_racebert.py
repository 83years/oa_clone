#!/usr/bin/env python3
"""
Infer author race/ethnicity using raceBERT.

This script:
1. Reads author data from DuckDB database
2. Uses raceBERT to infer race/ethnicity based on full name
3. Adds racebert_* columns to the database
4. Updates the database with inferred race/ethnicity and confidence scores

raceBERT uses a transformer-based model (RoBERTa) for state-of-the-art predictions:
- Race model: Predicts nh_white, nh_black, nh_api, nh_aian, nh_2prace, hispanic
- Ethnicity model: Predicts detailed ethnic categories
- Achieves 86% f1-score (4.1% improvement over previous state-of-the-art)

Based on: "raceBERT -- A Transformer-based Model for Predicting Race and Ethnicity from Names"
          (arXiv:2112.03807)

IMPORTANT: Requires PyTorch to be installed.
- PyTorch is not available for older Intel Macs
- Works on Apple Silicon Macs, Linux, and Windows with compatible hardware
- Install from: https://pytorch.org/get-started/locally/

If PyTorch is not available, this tool will gracefully skip and the pipeline
will continue with other tools.
"""

import sys
from pathlib import Path
import logging
from datetime import datetime
import argparse
import duckdb

# Check for PyTorch availability
PYTORCH_AVAILABLE = False
try:
    import torch
    PYTORCH_AVAILABLE = True
except ImportError:
    pass

# Check for raceBERT availability
RACEBERT_AVAILABLE = False
if PYTORCH_AVAILABLE:
    try:
        from racebert import RaceBERT
        RACEBERT_AVAILABLE = True
    except ImportError:
        pass

if not RACEBERT_AVAILABLE:
    print("="*70)
    print("WARNING: raceBERT not available")
    print("="*70)
    if not PYTORCH_AVAILABLE:
        print("PyTorch is not installed or not available for your system.")
        print()
        print("raceBERT requires PyTorch to run the transformer models.")
        print()
        print("To install PyTorch:")
        print("  Visit: https://pytorch.org/get-started/locally/")
        print("  Follow instructions for your system")
        print()
        print("Note: PyTorch is not available for Intel-based Macs.")
        print("      It works on Apple Silicon Macs, Linux, and Windows.")
    else:
        print("PyTorch is installed but raceBERT package is missing.")
        print()
        print("To install raceBERT:")
        print("  pip install racebert")
    print()
    print("If installation is not possible, you can skip this tool.")
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
    Check if raceBERT columns exist in the authors table and add them if not.

    Args:
        conn: DuckDB connection object

    Returns:
        None
    """
    logger = logging.getLogger(__name__)

    result = conn.execute("PRAGMA table_info(authors)").fetchall()
    existing_columns = {row[1] for row in result}

    columns_to_add = {
        'racebert_race': 'TEXT',
        'racebert_race_score': 'DOUBLE',
        'racebert_ethnicity': 'TEXT',
        'racebert_ethnicity_score': 'DOUBLE'
    }

    for col_name, col_type in columns_to_add.items():
        if col_name not in existing_columns:
            logger.info(f"Adding column: {col_name} ({col_type})")
            conn.execute(f"ALTER TABLE authors ADD COLUMN {col_name} {col_type}")
        else:
            logger.info(f"Column already exists: {col_name}")


def infer_ethnicity_in_duckdb(db_file, batch_size=100, use_gpu=False):
    """
    Infer race/ethnicity for authors in DuckDB database using raceBERT.

    This function:
    1. Connects to the DuckDB database
    2. Ensures raceBERT columns exist
    3. Initializes raceBERT models (race and ethnicity)
    4. Reads authors in batches
    5. Infers race and ethnicity for each author
    6. Updates the database with predictions and confidence scores
    7. Tracks inference statistics

    Args:
        db_file (Path): Path to DuckDB database file
        batch_size (int): Number of records to process in each batch (default: 100)
        use_gpu (bool): Whether to use GPU if available (default: False)

    Returns:
        None
    """
    logger = logging.getLogger(__name__)

    if not RACEBERT_AVAILABLE:
        logger.error("raceBERT is not available. Cannot proceed.")
        if not PYTORCH_AVAILABLE:
            logger.error("PyTorch is not installed.")
            logger.error("Visit: https://pytorch.org/get-started/locally/")
        else:
            logger.error("Install raceBERT with: pip install racebert")
        return

    logger.info("="*70)
    logger.info("RACE/ETHNICITY INFERENCE USING RACEBERT")
    logger.info("="*70)
    logger.info(f"Database: {db_file}")
    logger.info(f"Batch size: {batch_size:,}")
    logger.info(f"GPU enabled: {use_gpu}")
    logger.info("="*70)

    # Connect to DuckDB database
    conn = duckdb.connect(str(db_file))

    # Ensure columns exist
    ensure_columns_exist(conn)

    # Initialize raceBERT models
    logger.info("Loading raceBERT models (this may take a moment)...")
    try:
        device = 0 if use_gpu and torch.cuda.is_available() else -1

        race_model = RaceBERT(device=device)
        logger.info(f"Race model loaded (device: {'GPU' if device >= 0 else 'CPU'})")

        # Load ethnicity model
        ethnicity_model = RaceBERT(model_type='ethnicity', device=device)
        logger.info(f"Ethnicity model loaded (device: {'GPU' if device >= 0 else 'CPU'})")

    except Exception as e:
        logger.error(f"Failed to load raceBERT models: {e}")
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
    race_counts = {}
    ethnicity_counts = {}
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

        # Process each name
        updates = []

        for author_id, name in batch_results:
            try:
                # Predict race
                race_result = race_model.predict_race(name)
                race_label = race_result.get('label')
                race_score = race_result.get('score', 0.0)

                # Predict ethnicity
                ethnicity_result = ethnicity_model.predict_race(name)  # Note: method is still called predict_race
                ethnicity_label = ethnicity_result.get('label')
                ethnicity_score = ethnicity_result.get('score', 0.0)

                # Track statistics
                if race_label:
                    race_counts[race_label] = race_counts.get(race_label, 0) + 1
                if ethnicity_label:
                    ethnicity_counts[ethnicity_label] = ethnicity_counts.get(ethnicity_label, 0) + 1

                updates.append((race_label, race_score, ethnicity_label, ethnicity_score, author_id))

            except Exception as e:
                logger.warning(f"Error processing {name}: {e}")
                # Add null values for failed predictions
                updates.append((None, None, None, None, author_id))
                continue

        # Bulk update
        if updates:
            conn.executemany("""
                UPDATE authors
                SET racebert_race = ?,
                    racebert_race_score = ?,
                    racebert_ethnicity = ?,
                    racebert_ethnicity_score = ?
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
    logger.info("RACEBERT INFERENCE COMPLETE")
    logger.info("="*70)
    logger.info(f"Total records processed: {total_processed:,}")
    logger.info("")
    logger.info("Race Distribution:")
    for race in sorted(race_counts.keys()):
        count = race_counts[race]
        pct = (count / total_processed * 100) if total_processed > 0 else 0
        logger.info(f"  {race}: {count:,} ({pct:.2f}%)")
    logger.info("")
    logger.info("Top 10 Ethnicities:")
    top_ethnicities = sorted(ethnicity_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    for ethnicity, count in top_ethnicities:
        pct = (count / total_processed * 100) if total_processed > 0 else 0
        logger.info(f"  {ethnicity}: {count:,} ({pct:.2f}%)")
    logger.info("")
    logger.info(f"Total time: {total_elapsed:.2f} seconds")
    logger.info(f"Average rate: {avg_rate:.1f} records/sec")
    logger.info("="*70)


def main():
    """
    Main function to run race/ethnicity inference using raceBERT.

    Parses command-line arguments and initiates the inference process.
    """
    if not RACEBERT_AVAILABLE:
        print("ERROR: raceBERT is not available. Exiting.")
        return 1

    default_db_path = SCRIPT_DIR / 'datasets' / 'author_data.duckdb'

    parser = argparse.ArgumentParser(
        description='Infer author race/ethnicity using raceBERT.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default database (CPU)
  python 05_infer_racebert.py

  # Run with custom database
  python 05_infer_racebert.py --db datasets/my_authors.duckdb

  # Use GPU if available
  python 05_infer_racebert.py --gpu

  # Use custom batch size
  python 05_infer_racebert.py --batch-size 50

About raceBERT:
  raceBERT uses transformer-based models (RoBERTa) for state-of-the-art
  race and ethnicity prediction from names.

  Race categories:
  - nh_white: Non-Hispanic White
  - nh_black: Non-Hispanic Black
  - nh_api: Non-Hispanic Asian/Pacific Islander
  - nh_aian: Non-Hispanic American Indian/Alaska Native
  - nh_2prace: Non-Hispanic Two or More Races
  - hispanic: Hispanic

  Ethnicity categories: More detailed ethnic groups

  Performance: 86% f1-score (state-of-the-art)

  Note: Requires PyTorch. Processing is slower than simpler models but
        provides higher accuracy. GPU acceleration recommended for large datasets.
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

    parser.add_argument(
        '--gpu',
        action='store_true',
        help='Use GPU if available (default: CPU)'
    )

    args = parser.parse_args()

    logger = setup_logging()

    db_path = Path(args.db)

    if not db_path.exists():
        logger.error(f"Database file not found: {db_path}")
        return 1

    try:
        infer_ethnicity_in_duckdb(db_path, batch_size=args.batch_size, use_gpu=args.gpu)
        return 0
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())

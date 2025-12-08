#!/usr/bin/env python3
"""
Infer author gender using chicksexer (ML-based LSTM with cultural context).

This script:
1. Reads author data from DuckDB database
2. Uses chicksexer to infer gender based on full display name
3. Adds chicksexer_gender, chicksexer_male_prob, chicksexer_female_prob columns to database
4. Updates the database with inferred gender and probability scores

The chicksexer package uses character-level multilayer LSTM and considers
cultural context from surnames. Trained on DBpedia, US SSA data, and curated datasets.
Returns probability scores for male/female classification.
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
    from chicksexer import predict_gender, predict_genders
    CHICKSEXER_AVAILABLE = True
except ImportError:
    CHICKSEXER_AVAILABLE = False
    print("WARNING: chicksexer not installed. Install with: pip install chicksexer")


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
    Check if chicksexer columns exist in the authors table and add them if not.

    Args:
        conn: DuckDB connection object

    Returns:
        None
    """
    logger = logging.getLogger(__name__)

    result = conn.execute("PRAGMA table_info(authors)").fetchall()
    existing_columns = {row[1] for row in result}

    logger.info(f"Existing columns: {existing_columns}")

    if 'chicksexer_gender' not in existing_columns:
        logger.info("Adding column: chicksexer_gender (TEXT)")
        conn.execute("ALTER TABLE authors ADD COLUMN chicksexer_gender TEXT")
    else:
        logger.info("Column already exists: chicksexer_gender")

    if 'chicksexer_male_prob' not in existing_columns:
        logger.info("Adding column: chicksexer_male_prob (DOUBLE)")
        conn.execute("ALTER TABLE authors ADD COLUMN chicksexer_male_prob DOUBLE")
    else:
        logger.info("Column already exists: chicksexer_male_prob")

    if 'chicksexer_female_prob' not in existing_columns:
        logger.info("Adding column: chicksexer_female_prob (DOUBLE)")
        conn.execute("ALTER TABLE authors ADD COLUMN chicksexer_female_prob DOUBLE")
    else:
        logger.info("Column already exists: chicksexer_female_prob")


def infer_gender_in_duckdb(db_file, batch_size=100):
    """
    Infer gender for authors in DuckDB database using chicksexer.

    This function:
    1. Connects to the DuckDB database
    2. Ensures chicksexer columns exist
    3. Reads authors in batches
    4. Infers gender for each author based on display_name
    5. Updates the database with inferred gender and probabilities
    6. Tracks inference statistics

    Args:
        db_file (str or Path): Path to the DuckDB database file
        batch_size (int): Number of names to process per batch (chicksexer supports batching)

    Returns:
        tuple: (total_records, male_count, female_count, neutral_count)
    """
    logger = logging.getLogger(__name__)

    db_file = Path(db_file)

    if not db_file.exists():
        raise FileNotFoundError(f"Database file not found: {db_file}")

    logger.info(f"Database file: {db_file}")

    conn = duckdb.connect(str(db_file))
    logger.info("DuckDB connection established")

    logger.info("Checking for chicksexer columns...")
    ensure_columns_exist(conn)

    logger.info("Initializing chicksexer...")
    if not CHICKSEXER_AVAILABLE:
        raise ImportError("chicksexer package not available. Install with: pip install chicksexer")
    logger.info("chicksexer initialized successfully (will be loaded on first prediction)")

    count_query = """
        SELECT COUNT(*) FROM authors
        WHERE gender IS NULL OR gender != 'no_forename'
    """
    total_count = conn.execute(count_query).fetchone()[0]
    logger.info(f"Total authors to process: {total_count:,}")

    total_processed = 0
    male_count = 0
    female_count = 0
    neutral_count = 0
    start_time = datetime.now()

    logger.info("Starting gender inference...")

    offset = 0
    while offset < total_count:
        fetch_query = """
            SELECT author_id, display_name, forename
            FROM authors
            WHERE gender IS NULL OR gender != 'no_forename'
            LIMIT ? OFFSET ?
        """
        batch = conn.execute(fetch_query, [batch_size, offset]).fetchall()

        if not batch:
            break

        author_ids = []
        names = []

        for author_id, display_name, forename in batch:
            author_ids.append(author_id)
            name = display_name if display_name else (forename if forename else '')
            names.append(name)

        try:
            if len(names) > 1:
                predictions = predict_genders(names)
            else:
                predictions = [predict_gender(names[0])]

            updates = []
            for author_id, pred in zip(author_ids, predictions):
                if isinstance(pred, dict):
                    male_prob = pred.get('male', 0.0)
                    female_prob = pred.get('female', 0.0)

                    if male_prob > female_prob and male_prob > 0.5:
                        gender = 'male'
                        male_count += 1
                    elif female_prob > male_prob and female_prob > 0.5:
                        gender = 'female'
                        female_count += 1
                    else:
                        gender = 'neutral'
                        neutral_count += 1
                else:
                    gender = str(pred) if pred else 'neutral'
                    male_prob = 0.0
                    female_prob = 0.0

                    if gender == 'male':
                        male_count += 1
                    elif gender == 'female':
                        female_count += 1
                    else:
                        neutral_count += 1

                updates.append((gender, male_prob, female_prob, author_id))

        except Exception as e:
            logger.error(f"Batch prediction failed: {e}")
            updates = []
            for author_id in author_ids:
                updates.append(('neutral', 0.0, 0.0, author_id))
                neutral_count += 1

        conn.executemany(
            """
            UPDATE authors
            SET chicksexer_gender = ?,
                chicksexer_male_prob = ?,
                chicksexer_female_prob = ?
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
            f"Rate: {rate:.1f} records/sec | "
            f"Male: {male_count:,} | Female: {female_count:,} | Neutral: {neutral_count:,}"
        )

    conn.close()
    logger.info("DuckDB connection closed")

    total_elapsed = (datetime.now() - start_time).total_seconds()
    avg_rate = total_processed / total_elapsed if total_elapsed > 0 else 0
    success_rate = ((male_count + female_count) / total_processed * 100) if total_processed > 0 else 0

    logger.info("="*70)
    logger.info("CHICKSEXER GENDER INFERENCE COMPLETE")
    logger.info("="*70)
    logger.info(f"Total records processed: {total_processed:,}")
    logger.info("")
    logger.info("Gender Distribution:")
    logger.info(f"  Male: {male_count:,} ({male_count/total_processed*100:.2f}%)" if total_processed > 0 else "N/A")
    logger.info(f"  Female: {female_count:,} ({female_count/total_processed*100:.2f}%)" if total_processed > 0 else "N/A")
    logger.info(f"  Neutral: {neutral_count:,} ({neutral_count/total_processed*100:.2f}%)" if total_processed > 0 else "N/A")
    logger.info(f"  Success rate (M/F): {success_rate:.2f}%")
    logger.info("")
    logger.info(f"Total time: {total_elapsed:.2f} seconds")
    logger.info(f"Average rate: {avg_rate:.1f} records/sec")
    logger.info("="*70)

    return total_processed, male_count, female_count, neutral_count


def main():
    """
    Main entry point for the script.

    Parses command line arguments and initiates the gender inference process.
    """
    default_db_path = SCRIPT_DIR / 'datasets' / 'author_data.duckdb'

    parser = argparse.ArgumentParser(
        description='Infer author gender using chicksexer (LSTM with cultural context).',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Infer gender from default database
  python 14_infer_chicksexer.py

  # Infer gender with custom batch size
  python 14_infer_chicksexer.py --batch-size 50

  # Infer gender with custom database file
  python 14_infer_chicksexer.py --db datasets/my_authors.duckdb

Gender inference:
  - Uses character-level multilayer LSTM
  - Considers cultural context from surnames
  - Returns probability scores for male/female
  - Handles ambiguous names and typos
  - Results stored in chicksexer_gender, chicksexer_male_prob, chicksexer_female_prob columns

Note:
  - chicksexer requires TensorFlow (slower than lookup-based methods)
  - First prediction will be slower as model loads
  - Recommended batch size: 50-100 for balance of speed and accuracy
        """
    )

    parser.add_argument(
        '--db',
        type=str,
        default=str(default_db_path),
        help=f'Path to the DuckDB database file containing author data (default: {default_db_path})'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=100,
        help='Number of names to process per batch (default: 100)'
    )

    args = parser.parse_args()

    logger = setup_logging()

    logger.info("="*70)
    logger.info("AUTHOR GENDER INFERENCE WITH CHICKSEXER")
    logger.info("="*70)
    logger.info(f"Database file: {args.db}")
    logger.info(f"Batch size: {args.batch_size}")
    logger.info("="*70)

    try:
        total_records, male, female, neutral = infer_gender_in_duckdb(
            db_file=args.db,
            batch_size=args.batch_size
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

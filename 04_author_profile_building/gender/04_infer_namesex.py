#!/usr/bin/env python3
"""
Infer author gender using namesex (ML-based gender prediction).

This script:
1. Reads author data from DuckDB database
2. Uses namesex to infer gender based on forename
3. Adds namesex_gender and namesex_prob columns to the database
4. Updates the database with inferred gender and probability scores

The namesex package uses Random Forest classifier with word2vec features.
Returns gender predictions with probability scores.

NOTE: namesex may have compatibility issues with newer Python/scikit-learn versions.
This script includes graceful error handling.
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
    from namesex.namesex import namesex as NameSexClassifier
    NAMESEX_AVAILABLE = True
except ImportError as e:
    NAMESEX_AVAILABLE = False
    print(f"WARNING: namesex not available: {e}")
    print("Install with: pip install namesex scikit-learn")


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
    Check if namesex columns exist in the authors table and add them if not.

    Args:
        conn: DuckDB connection object

    Returns:
        None
    """
    logger = logging.getLogger(__name__)

    result = conn.execute("PRAGMA table_info(authors)").fetchall()
    existing_columns = {row[1] for row in result}

    logger.info(f"Existing columns: {existing_columns}")

    if 'namesex_gender' not in existing_columns:
        logger.info("Adding column: namesex_gender (TEXT)")
        conn.execute("ALTER TABLE authors ADD COLUMN namesex_gender TEXT")
    else:
        logger.info("Column already exists: namesex_gender")

    if 'namesex_prob' not in existing_columns:
        logger.info("Adding column: namesex_prob (DOUBLE)")
        conn.execute("ALTER TABLE authors ADD COLUMN namesex_prob DOUBLE")
    else:
        logger.info("Column already exists: namesex_prob")


def infer_gender_in_duckdb(db_file):
    """
    Infer gender for authors in DuckDB database using namesex.

    This function:
    1. Connects to the DuckDB database
    2. Ensures namesex columns exist
    3. Reads authors in batches
    4. Infers gender for each author based on forename
    5. Updates the database with inferred gender and probabilities
    6. Tracks inference statistics

    Args:
        db_file (str or Path): Path to the DuckDB database file

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

    logger.info("Checking for namesex columns...")
    ensure_columns_exist(conn)

    logger.info("Initializing namesex...")
    if not NAMESEX_AVAILABLE:
        raise ImportError(
            "namesex package not available. Install with: pip install namesex scikit-learn\n"
            "NOTE: namesex may have compatibility issues with newer Python versions."
        )

    try:
        ns = NameSexClassifier()
        logger.info("namesex initialized successfully")
    except Exception as e:
        raise RuntimeError(f"Failed to initialize namesex: {e}\nThis may be a compatibility issue with scikit-learn version.")

    count_query = """
        SELECT COUNT(*) FROM authors
        WHERE gender IS NULL OR gender != 'no_forename'
    """
    total_count = conn.execute(count_query).fetchone()[0]
    logger.info(f"Total authors to process: {total_count:,}")

    batch_size = 1000
    total_processed = 0
    male_count = 0
    female_count = 0
    unknown_count = 0
    error_count = 0
    start_time = datetime.now()

    logger.info("Starting gender inference...")

    offset = 0
    while offset < total_count:
        fetch_query = """
            SELECT author_id, forename, country_name
            FROM authors
            WHERE gender IS NULL OR gender != 'no_forename'
            LIMIT ? OFFSET ?
        """
        batch = conn.execute(fetch_query, [batch_size, offset]).fetchall()

        if not batch:
            break

        author_ids = []
        forenames = []

        for author_id, forename, country_name in batch:
            author_ids.append(author_id)
            forenames.append(forename if forename else '')

        try:
            predictions = ns.predict(forenames, predprob=True)

            updates = []
            for i, (author_id, pred) in enumerate(zip(author_ids, predictions)):
                if isinstance(pred, tuple) and len(pred) == 2:
                    gender, prob = pred
                    if gender == 0:
                        gender_str = 'female'
                    elif gender == 1:
                        gender_str = 'male'
                    else:
                        gender_str = 'unknown'

                    prob_value = float(prob) if prob else 0.0
                else:
                    gender_str = 'unknown'
                    prob_value = 0.0

                if gender_str == 'male':
                    male_count += 1
                elif gender_str == 'female':
                    female_count += 1
                else:
                    unknown_count += 1

                updates.append((gender_str, prob_value, author_id))

        except Exception as e:
            logger.error(f"Batch prediction failed: {e}")
            updates = []
            for author_id in author_ids:
                updates.append(('unknown', 0.0, author_id))
                unknown_count += 1
            error_count += len(author_ids)

        conn.executemany(
            """
            UPDATE authors
            SET namesex_gender = ?,
                namesex_prob = ?
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
    logger.info("NAMESEX GENDER INFERENCE COMPLETE")
    logger.info("="*70)
    logger.info(f"Total records processed: {total_processed:,}")
    logger.info(f"Errors encountered: {error_count:,}")
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
        description='Infer author gender using namesex (ML-based Random Forest classifier).',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Infer gender from default database
  python 12_infer_namesex.py

  # Infer gender with custom database file
  python 12_infer_namesex.py --db datasets/my_authors.duckdb

Gender inference:
  - Uses Random Forest classifier with word2vec features
  - Returns: 'male', 'female', or 'unknown' with probability scores
  - General purpose, not region-specific
  - Results stored in namesex_gender and namesex_prob columns

Compatibility Note:
  - namesex may have compatibility issues with newer Python/scikit-learn versions
  - If you encounter errors, try: pip install scikit-learn==0.24.2
        """
    )

    parser.add_argument(
        '--db',
        type=str,
        default=str(default_db_path),
        help=f'Path to the DuckDB database file containing author data (default: {default_db_path})'
    )

    args = parser.parse_args()

    logger = setup_logging()

    logger.info("="*70)
    logger.info("AUTHOR GENDER INFERENCE WITH NAMESEX")
    logger.info("="*70)
    logger.info(f"Database file: {args.db}")
    logger.info("="*70)

    try:
        total_records, male, female, unknown = infer_gender_in_duckdb(
            db_file=args.db
        )

        logger.info("Script completed successfully")
        return 0

    except FileNotFoundError as e:
        logger.error(f"File error: {e}")
        return 1
    except ImportError as e:
        logger.error(f"Import error: {e}")
        return 1
    except RuntimeError as e:
        logger.error(f"Runtime error: {e}")
        return 1
    except duckdb.Error as e:
        logger.error(f"DuckDB error: {e}")
        return 1
    except Exception as e:
        logger.critical(f"Script failed with error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())

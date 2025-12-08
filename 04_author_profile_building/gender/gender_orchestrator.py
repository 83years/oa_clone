#!/usr/bin/env python3
"""
Gender Inference Orchestrator

This script orchestrates the execution of multiple gender inference tools
and combines their results using consensus logic.

Tools included:
1. genderComputer (general)
2. gender-guesser (general)
3. genderpred-in (India-specific)
4. namesex (Chinese names, ML-based)
5. persian-gender-detection (Iran-specific)
6. chicksexer (cultural context aware)
7. genderizer3 (Turkish/multilingual)

The orchestrator:
- Runs each tool in sequence
- Logs progress for each tool
- Combines results using population-weighted consensus
- Generates final gender predictions with confidence scores
"""

import sys
from pathlib import Path
import logging
from datetime import datetime
import argparse
import subprocess
import duckdb

SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(PARENT_DIR))

from gender_consensus import calculate_consensus


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


def run_tool(script_name: str, db_path: Path, extra_args: list = None) -> bool:
    """
    Run a gender inference tool script.

    Args:
        script_name (str): Name of the script to run
        db_path (Path): Path to the database
        extra_args (list, optional): Additional command line arguments

    Returns:
        bool: True if successful, False otherwise
    """
    logger = logging.getLogger(__name__)

    script_path = SCRIPT_DIR / script_name

    if not script_path.exists():
        logger.warning(f"Script not found: {script_name} - skipping")
        return False

    logger.info("="*70)
    logger.info(f"Running: {script_name}")
    logger.info("="*70)

    cmd = [sys.executable, str(script_path), '--db', str(db_path)]

    if extra_args:
        cmd.extend(extra_args)

    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=False,
            text=True
        )
        logger.info(f"✓ {script_name} completed successfully")
        return True

    except subprocess.CalledProcessError as e:
        logger.error(f"✗ {script_name} failed with exit code {e.returncode}")
        return False
    except Exception as e:
        logger.error(f"✗ {script_name} failed with error: {e}")
        return False


def ensure_consensus_columns(conn):
    """
    Ensure consensus columns exist in the authors table.

    Args:
        conn: DuckDB connection object

    Returns:
        None
    """
    logger = logging.getLogger(__name__)

    result = conn.execute("PRAGMA table_info(authors)").fetchall()
    existing_columns = {row[1] for row in result}

    if 'consensus_gender' not in existing_columns:
        logger.info("Adding column: consensus_gender (TEXT)")
        conn.execute("ALTER TABLE authors ADD COLUMN consensus_gender TEXT")
    else:
        logger.info("Column already exists: consensus_gender")

    if 'consensus_confidence' not in existing_columns:
        logger.info("Adding column: consensus_confidence (DOUBLE)")
        conn.execute("ALTER TABLE authors ADD COLUMN consensus_confidence DOUBLE")
    else:
        logger.info("Column already exists: consensus_confidence")

    if 'consensus_votes' not in existing_columns:
        logger.info("Adding column: consensus_votes (TEXT)")
        conn.execute("ALTER TABLE authors ADD COLUMN consensus_votes TEXT")
    else:
        logger.info("Column already exists: consensus_votes")


def calculate_and_store_consensus(db_path: Path):
    """
    Calculate consensus gender from all tool predictions and store in database.

    Args:
        db_path (Path): Path to the database

    Returns:
        tuple: (total_processed, male_count, female_count, uncertain_count)
    """
    logger = logging.getLogger(__name__)

    logger.info("="*70)
    logger.info("CALCULATING CONSENSUS GENDER")
    logger.info("="*70)

    conn = duckdb.connect(str(db_path))

    ensure_consensus_columns(conn)

    query = """
        SELECT
            author_id,
            country_name,
            gendercomputer_gender,
            genderguesser_gender,
            genderpred_in_gender,
            genderpred_in_male_prob,
            genderpred_in_female_prob,
            namesex_gender,
            namesex_prob,
            persian_gender,
            genderizer3_gender,
            chicksexer_gender,
            chicksexer_male_prob,
            chicksexer_female_prob
        FROM authors
        WHERE gender IS NULL OR gender != 'no_forename'
    """

    logger.info("Fetching author data for consensus calculation...")
    results = conn.execute(query).fetchall()
    total_count = len(results)
    logger.info(f"Processing {total_count:,} authors")

    batch_size = 10000
    total_processed = 0
    male_count = 0
    female_count = 0
    uncertain_count = 0
    start_time = datetime.now()

    for offset in range(0, total_count, batch_size):
        batch = results[offset:offset + batch_size]
        updates = []

        for row in batch:
            (
                author_id, country_name,
                gc_gender, gg_gender,
                gpi_gender, gpi_male_prob, gpi_female_prob,
                ns_gender, ns_prob,
                persian_gender,
                g3_gender,
                cs_gender, cs_male_prob, cs_female_prob
            ) = row

            consensus, confidence, votes = calculate_consensus(
                gendercomputer=gc_gender,
                genderguesser=gg_gender,
                genderpred_in=gpi_gender,
                genderpred_in_male_prob=gpi_male_prob,
                genderpred_in_female_prob=gpi_female_prob,
                namesex=ns_gender,
                namesex_prob=ns_prob,
                persian=persian_gender,
                genderizer3=g3_gender,
                chicksexer=cs_gender,
                chicksexer_male_prob=cs_male_prob,
                chicksexer_female_prob=cs_female_prob,
                country=country_name
            )

            if consensus == 'male':
                male_count += 1
            elif consensus == 'female':
                female_count += 1
            else:
                uncertain_count += 1

            vote_json = str(votes)
            updates.append((consensus if consensus else '', confidence, vote_json, author_id))

        conn.executemany(
            """
            UPDATE authors
            SET consensus_gender = ?,
                consensus_confidence = ?,
                consensus_votes = ?
            WHERE author_id = ?
            """,
            updates
        )

        total_processed += len(batch)

        elapsed = (datetime.now() - start_time).total_seconds()
        rate = total_processed / elapsed if elapsed > 0 else 0
        pct_complete = (total_processed / total_count * 100) if total_count > 0 else 0

        logger.info(
            f"Progress: {total_processed:,}/{total_count:,} ({pct_complete:.1f}%) | "
            f"Rate: {rate:.0f} records/sec | "
            f"Male: {male_count:,} | Female: {female_count:,} | Uncertain: {uncertain_count:,}"
        )

    conn.close()

    total_elapsed = (datetime.now() - start_time).total_seconds()
    avg_rate = total_processed / total_elapsed if total_elapsed > 0 else 0
    success_rate = ((male_count + female_count) / total_processed * 100) if total_processed > 0 else 0

    logger.info("="*70)
    logger.info("CONSENSUS CALCULATION COMPLETE")
    logger.info("="*70)
    logger.info(f"Total records processed: {total_processed:,}")
    logger.info("")
    logger.info("Consensus Gender Distribution:")
    logger.info(f"  Male: {male_count:,} ({male_count/total_processed*100:.2f}%)" if total_processed > 0 else "N/A")
    logger.info(f"  Female: {female_count:,} ({female_count/total_processed*100:.2f}%)" if total_processed > 0 else "N/A")
    logger.info(f"  Uncertain: {uncertain_count:,} ({uncertain_count/total_processed*100:.2f}%)" if total_processed > 0 else "N/A")
    logger.info(f"  Success rate: {success_rate:.2f}%")
    logger.info("")
    logger.info(f"Total time: {total_elapsed:.2f} seconds")
    logger.info(f"Average rate: {avg_rate:.0f} records/sec")
    logger.info("="*70)

    return total_processed, male_count, female_count, uncertain_count


def main():
    """
    Main orchestrator function.

    Runs all gender inference tools in sequence and calculates consensus.
    """
    default_db_path = SCRIPT_DIR / 'datasets' / 'author_data.duckdb'

    parser = argparse.ArgumentParser(
        description='Gender Inference Orchestrator - runs all tools and calculates consensus.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tools with default database
  python gender_orchestrator.py

  # Run with custom database
  python gender_orchestrator.py --db datasets/my_authors.duckdb

  # Skip specific tools
  python gender_orchestrator.py --skip chicksexer --skip namesex

  # Only run specific tools
  python gender_orchestrator.py --only gendercomputer genderguesser

Tools:
  - gendercomputer: General purpose (using genderComputer)
  - genderguesser: General purpose (using gender-guesser)
  - genderpred_in: India-specific (using genderpred-in)
  - namesex: Chinese names (using namesex)
  - persian: Iran-specific (using persian-gender-detection)
  - chicksexer: Cultural context aware (using chicksexer)
  - genderizer3: Turkish/multilingual (using genderizer3)

The orchestrator will:
1. Run each selected tool in sequence
2. Log progress for monitoring
3. Calculate weighted consensus based on population
4. Store results in consensus_gender, consensus_confidence, consensus_votes columns
        """
    )

    parser.add_argument(
        '--db',
        type=str,
        default=str(default_db_path),
        help=f'Path to the DuckDB database file (default: {default_db_path})'
    )

    parser.add_argument(
        '--skip',
        action='append',
        choices=['gendercomputer', 'genderguesser', 'genderpred_in', 'namesex', 'persian', 'chicksexer', 'genderizer3'],
        help='Skip specific tools (can be specified multiple times)'
    )

    parser.add_argument(
        '--only',
        nargs='+',
        choices=['gendercomputer', 'genderguesser', 'genderpred_in', 'namesex', 'persian', 'chicksexer', 'genderizer3'],
        help='Only run specific tools (space-separated list)'
    )

    args = parser.parse_args()

    logger = setup_logging()

    db_path = Path(args.db)

    logger.info("="*70)
    logger.info("GENDER INFERENCE ORCHESTRATOR")
    logger.info("="*70)
    logger.info(f"Database: {db_path}")
    logger.info("="*70)

    skip_tools = set(args.skip) if args.skip else set()
    only_tools = set(args.only) if args.only else None

    tool_scripts = {
        'gendercomputer': '01_infer_genderComputer.py',
        'genderguesser': '02_infer_genderGuesser.py',
        'genderpred_in': '03_infer_genderpred_in.py',
        'namesex': '04_infer_namesex.py',
        'persian': '05_infer_persian_gender.py',
        'chicksexer': '06_infer_chicksexer.py',
        'genderizer3': '07_infer_genderizer3.py'
    }

    results = {}
    start_time = datetime.now()

    for tool_name, script_name in tool_scripts.items():
        if only_tools and tool_name not in only_tools:
            logger.info(f"Skipping {tool_name} (not in --only list)")
            continue

        if tool_name in skip_tools:
            logger.info(f"Skipping {tool_name} (in --skip list)")
            continue

        success = run_tool(script_name, db_path)
        results[tool_name] = success

    logger.info("="*70)
    logger.info("TOOL EXECUTION SUMMARY")
    logger.info("="*70)

    for tool_name, success in results.items():
        status = "✓ SUCCESS" if success else "✗ FAILED"
        logger.info(f"{tool_name:20s}: {status}")

    logger.info("="*70)

    try:
        total, male, female, uncertain = calculate_and_store_consensus(db_path)
    except Exception as e:
        logger.error(f"Consensus calculation failed: {e}", exc_info=True)
        return 1

    total_elapsed = (datetime.now() - start_time).total_seconds()

    logger.info("="*70)
    logger.info("ORCHESTRATOR COMPLETE")
    logger.info("="*70)
    logger.info(f"Total pipeline time: {total_elapsed:.2f} seconds ({total_elapsed/60:.1f} minutes)")
    logger.info("="*70)

    return 0


if __name__ == '__main__':
    sys.exit(main())

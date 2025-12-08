#!/usr/bin/env python3
"""
Ethnicity Inference Orchestrator

This script orchestrates the execution of multiple ethnicity inference tools
and combines their results using consensus logic.

Tools included:
1. ethnicseer - 12 ethnic categories (Chinese, English, French, German, Indian,
   Italian, Japanese, Korean, Middle-Eastern, Russian, Spanish, Vietnamese)
2. pyethnicity - US-centric race prediction (Asian, Black, Hispanic, White)
3. ethnidata - Nationality/country prediction with regional context (238 countries)
4. name2nat - 254 nationalities from Wikipedia data (global coverage)
5. raceBERT - Transformer-based race/ethnicity (state-of-the-art, requires PyTorch)

The orchestrator:
- Runs each tool in sequence
- Logs progress for each tool
- Combines results using weighted consensus
- Maps predictions to unified ethnicity categories
- Generates final ethnicity predictions with confidence scores
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

from ethnicity_consensus import calculate_consensus


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
    Run an ethnicity inference tool script.

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

    if 'consensus_ethnicity' not in existing_columns:
        logger.info("Adding column: consensus_ethnicity (TEXT)")
        conn.execute("ALTER TABLE authors ADD COLUMN consensus_ethnicity TEXT")
    else:
        logger.info("Column already exists: consensus_ethnicity")

    if 'consensus_ethnicity_confidence' not in existing_columns:
        logger.info("Adding column: consensus_ethnicity_confidence (DOUBLE)")
        conn.execute("ALTER TABLE authors ADD COLUMN consensus_ethnicity_confidence DOUBLE")
    else:
        logger.info("Column already exists: consensus_ethnicity_confidence")

    if 'consensus_ethnicity_votes' not in existing_columns:
        logger.info("Adding column: consensus_ethnicity_votes (TEXT)")
        conn.execute("ALTER TABLE authors ADD COLUMN consensus_ethnicity_votes TEXT")
    else:
        logger.info("Column already exists: consensus_ethnicity_votes")


def calculate_and_store_consensus(db_path: Path):
    """
    Calculate consensus ethnicity from all tool predictions and store in database.

    Args:
        db_path (Path): Path to the database

    Returns:
        tuple: (total_processed, ethnicity_counts)
    """
    logger = logging.getLogger(__name__)

    logger.info("="*70)
    logger.info("CALCULATING CONSENSUS ETHNICITY")
    logger.info("="*70)

    conn = duckdb.connect(str(db_path))

    ensure_consensus_columns(conn)

    query = """
        SELECT
            author_id,
            ethnicseer_ethnicity,
            ethnicseer_confidence,
            pyethnicity_asian,
            pyethnicity_black,
            pyethnicity_hispanic,
            pyethnicity_white,
            ethnidata_country_name,
            ethnidata_region,
            ethnidata_confidence,
            name2nat_nationality1,
            name2nat_probability1,
            racebert_race,
            racebert_race_score
        FROM authors
        WHERE display_name IS NOT NULL
    """

    logger.info("Fetching author data for consensus calculation...")
    results = conn.execute(query).fetchall()
    total_count = len(results)
    logger.info(f"Processing {total_count:,} authors")

    batch_size = 10000
    total_processed = 0
    ethnicity_counts = {}
    start_time = datetime.now()

    for offset in range(0, total_count, batch_size):
        batch = results[offset:offset + batch_size]
        updates = []

        for row in batch:
            (
                author_id,
                ethnicseer_ethnicity, ethnicseer_confidence,
                pyethnicity_asian, pyethnicity_black, pyethnicity_hispanic, pyethnicity_white,
                ethnidata_country, ethnidata_region, ethnidata_confidence,
                name2nat_nationality, name2nat_probability,
                racebert_race, racebert_score
            ) = row

            consensus, confidence, votes = calculate_consensus(
                ethnicseer_ethnicity=ethnicseer_ethnicity,
                ethnicseer_confidence=ethnicseer_confidence,
                pyethnicity_asian=pyethnicity_asian,
                pyethnicity_black=pyethnicity_black,
                pyethnicity_hispanic=pyethnicity_hispanic,
                pyethnicity_white=pyethnicity_white,
                ethnidata_country=ethnidata_country,
                ethnidata_region=ethnidata_region,
                ethnidata_confidence=ethnidata_confidence,
                name2nat_nationality=name2nat_nationality,
                name2nat_probability=name2nat_probability,
                racebert_race=racebert_race,
                racebert_score=racebert_score
            )

            if consensus:
                ethnicity_counts[consensus] = ethnicity_counts.get(consensus, 0) + 1

            vote_json = str(votes) if votes else ''
            updates.append((consensus if consensus else '', confidence, vote_json, author_id))

        conn.executemany(
            """
            UPDATE authors
            SET consensus_ethnicity = ?,
                consensus_ethnicity_confidence = ?,
                consensus_ethnicity_votes = ?
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
            f"Rate: {rate:.0f} records/sec"
        )

    conn.close()

    total_elapsed = (datetime.now() - start_time).total_seconds()
    avg_rate = total_processed / total_elapsed if total_elapsed > 0 else 0

    logger.info("="*70)
    logger.info("CONSENSUS CALCULATION COMPLETE")
    logger.info("="*70)
    logger.info(f"Total records processed: {total_processed:,}")
    logger.info("")
    logger.info("Consensus Ethnicity Distribution:")
    for ethnicity in sorted(ethnicity_counts.keys()):
        count = ethnicity_counts[ethnicity]
        pct = (count / total_processed * 100) if total_processed > 0 else 0
        logger.info(f"  {ethnicity}: {count:,} ({pct:.2f}%)")
    logger.info("")
    logger.info(f"Total time: {total_elapsed:.2f} seconds")
    logger.info(f"Average rate: {avg_rate:.0f} records/sec")
    logger.info("="*70)

    return total_processed, ethnicity_counts


def main():
    """
    Main orchestrator function.

    Runs all ethnicity inference tools in sequence and calculates consensus.
    """
    default_db_path = SCRIPT_DIR / 'datasets' / 'author_data.duckdb'

    parser = argparse.ArgumentParser(
        description='Ethnicity Inference Orchestrator - runs all tools and calculates consensus.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run all tools with default database
  python ethnicity_orchestrator.py

  # Run with custom database
  python ethnicity_orchestrator.py --db datasets/my_authors.duckdb

  # Skip specific tools (e.g., tools requiring PyTorch)
  python ethnicity_orchestrator.py --skip racebert --skip name2nat

  # Only run specific tools
  python ethnicity_orchestrator.py --only ethnicseer ethnidata

Tools:
  - ethnicseer: 12 ethnic categories (Chinese, English, French, German, Indian,
    Italian, Japanese, Korean, Middle-Eastern, Russian, Spanish, Vietnamese)
  - pyethnicity: US-centric race prediction (Asian, Black, Hispanic, White)
  - ethnidata: Nationality/country prediction (238 countries) with regional context
  - name2nat: 254 nationalities from Wikipedia (global coverage, may have dependencies)
  - racebert: Transformer-based state-of-the-art (requires PyTorch, not available on Intel Macs)

Note: name2nat and racebert will gracefully skip if dependencies are not available.

The orchestrator will:
1. Run each selected tool in sequence
2. Log progress for monitoring
3. Calculate weighted consensus with unified ethnicity categories
4. Store results in consensus_ethnicity, consensus_ethnicity_confidence,
   consensus_ethnicity_votes columns

Unified Ethnicity Categories:
  - East Asian
  - South Asian
  - Southeast Asian
  - Middle Eastern/North African
  - Hispanic/Latino
  - European
  - Sub-Saharan African
  - African/African American
  - Oceanian
  - Other/Mixed
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
        choices=['ethnicseer', 'pyethnicity', 'ethnidata', 'name2nat', 'racebert'],
        help='Skip specific tools (can be specified multiple times)'
    )

    parser.add_argument(
        '--only',
        nargs='+',
        choices=['ethnicseer', 'pyethnicity', 'ethnidata', 'name2nat', 'racebert'],
        help='Only run specific tools (space-separated list)'
    )

    args = parser.parse_args()

    logger = setup_logging()

    db_path = Path(args.db)

    logger.info("="*70)
    logger.info("ETHNICITY INFERENCE ORCHESTRATOR")
    logger.info("="*70)
    logger.info(f"Database: {db_path}")
    logger.info("="*70)

    skip_tools = set(args.skip) if args.skip else set()
    only_tools = set(args.only) if args.only else None

    tool_scripts = {
        'ethnicseer': '01_infer_ethnicseer.py',
        'pyethnicity': '02_infer_pyethnicity.py',
        'ethnidata': '03_infer_ethnidata.py',
        'name2nat': '04_infer_name2nat.py',
        'racebert': '05_infer_racebert.py'
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
        total, ethnicity_counts = calculate_and_store_consensus(db_path)
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

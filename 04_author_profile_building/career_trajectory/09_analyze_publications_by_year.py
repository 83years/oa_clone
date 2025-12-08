#!/usr/bin/env python3
"""
Analyze publication patterns for random authors with ORCID IDs.

This script:
1. Connects to the PostgreSQL database (oadbv5)
2. Selects 100,000 random authors where orcid IS NOT NULL AND works_count > 10
3. Queries publication counts per year in batches of 100 authors
4. Outputs results to DuckDB showing works published per year across their career

OPTIMIZATIONS:
- Pre-filters for authors with works_count > 10 (removes ~50% of authors)
- Batch processing: queries 100 authors at once instead of one-by-one
- DuckDB storage: Fast columnar database for analytical queries
- This reduces query count from 100,000 to 1,000, dramatically improving speed

CRITICAL: Uses works, authors, and authorship tables directly.
         Does NOT use the authors_works_by_year table.
"""

import sys
from pathlib import Path
import logging
from datetime import datetime
import argparse
import duckdb
import psycopg2
from psycopg2.extras import RealDictCursor

# Add parent directory to path for config imports
SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(PARENT_DIR))

from config import DB_CONFIG


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


def get_random_authors_with_orcid(cursor, sample_size=100000, min_works=10):
    """
    Select random authors where orcid IS NOT NULL and works_count > min_works.

    Args:
        cursor: PostgreSQL cursor
        sample_size (int): Number of authors to sample
        min_works (int): Minimum number of works (default: 10)

    Returns:
        list: List of author dictionaries
    """
    logger = logging.getLogger(__name__)

    query = """
    SELECT author_id, orcid, display_name, works_count
    FROM authors
    WHERE orcid IS NOT NULL
      AND works_count > %s
    ORDER BY RANDOM()
    LIMIT %s
    """

    logger.info(f"Selecting {sample_size} random authors with ORCID and works_count > {min_works}...")
    cursor.execute(query, (min_works, sample_size))
    results = cursor.fetchall()

    logger.info(f"Selected {len(results)} authors")

    return results


def get_publications_by_year_batch(cursor, author_ids):
    """
    Get publication counts per year for multiple authors in a single query.

    Queries works table through authorship table to get publication_year
    for all works by the specified authors.

    Args:
        cursor: PostgreSQL cursor
        author_ids (list): List of author IDs

    Returns:
        dict: Dictionary mapping author_id -> {year -> count}
    """
    query = """
    SELECT
        a.author_id,
        w.publication_year,
        COUNT(*) as work_count
    FROM authorship a
    JOIN works w ON a.work_id = w.work_id
    WHERE a.author_id = ANY(%s)
        AND w.publication_year IS NOT NULL
    GROUP BY a.author_id, w.publication_year
    ORDER BY a.author_id, w.publication_year
    """

    cursor.execute(query, (author_ids,))
    results = cursor.fetchall()

    # Convert to nested dictionary: author_id -> {year -> count}
    author_year_counts = {}
    for row in results:
        author_id = row['author_id']
        year = row['publication_year']
        count = row['work_count']

        if author_id not in author_year_counts:
            author_year_counts[author_id] = {}

        author_year_counts[author_id][year] = count

    return author_year_counts


def analyze_publication_patterns(sample_size=100000, min_works=10, output_filename=None):
    """
    Main analysis function.

    Selects random authors with ORCID and analyzes their publication
    patterns across their entire career.

    Args:
        sample_size (int): Number of authors to analyze
        min_works (int): Minimum number of works to filter authors
        output_filename (str, optional): Custom output filename

    Returns:
        tuple: (output_file_path, total_authors_analyzed)
    """
    logger = logging.getLogger(__name__)

    # Setup output file
    if output_filename is None:
        output_filename = f'author_publications_by_year_{datetime.now():%Y%m%d_%H%M%S}.duckdb'

    datasets_dir = SCRIPT_DIR / 'datasets'
    datasets_dir.mkdir(exist_ok=True)
    output_file = datasets_dir / output_filename

    logger.info(f"Output DuckDB file: {output_file}")

    # Connect to PostgreSQL
    logger.info(f"Connecting to PostgreSQL: {DB_CONFIG['database']} at {DB_CONFIG['host']}:{DB_CONFIG['port']}")

    try:
        pg_conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
        pg_cursor = pg_conn.cursor()
        logger.info("PostgreSQL connection established")

        # Connect to DuckDB
        logger.info(f"Connecting to DuckDB: {output_file}")
        duck_conn = duckdb.connect(str(output_file))
        logger.info("DuckDB connection established")

        # Create DuckDB table
        duck_conn.execute("""
            CREATE TABLE IF NOT EXISTS author_publications_by_year (
                author_id TEXT,
                orcid TEXT,
                display_name TEXT,
                publication_year INTEGER,
                works_count INTEGER,
                total_career_works INTEGER,
                first_pub_year INTEGER,
                last_pub_year INTEGER,
                career_length_years INTEGER
            )
        """)
        logger.info("DuckDB table created (or already exists)")

        # Clear existing data if table exists
        duck_conn.execute("DELETE FROM author_publications_by_year")
        logger.info("Cleared existing data from DuckDB table")

        # Get random authors
        authors = get_random_authors_with_orcid(pg_cursor, sample_size, min_works=min_works)

        if not authors:
            logger.warning(f"No authors found with ORCID and works_count > {min_works}!")
            return None, 0

        # Start publication analysis
        logger.info("Starting publication analysis...")
        logger.info(f"Processing {len(authors)} authors in batches of 100...")

        start_time = datetime.now()
        authors_analyzed = 0
        total_author_work_records = 0
        batch_size = 100

        # Process authors in batches
        for batch_start in range(0, len(authors), batch_size):
            batch_end = min(batch_start + batch_size, len(authors))
            batch_authors = authors[batch_start:batch_end]

            # Extract author IDs for batch query
            author_ids = [author['author_id'] for author in batch_authors]

            # Get publication data for entire batch in one query
            batch_year_counts = get_publications_by_year_batch(pg_cursor, author_ids)

            # Prepare batch data for DuckDB
            duck_batch_data = []

            # Process each author in the batch
            for author in batch_authors:
                author_id = author['author_id']
                orcid = author['orcid']
                display_name = author['display_name']

                # Get this author's year counts from batch results
                year_counts = batch_year_counts.get(author_id, {})

                if not year_counts:
                    logger.warning(f"Author {author_id} has no publications with years")
                    continue

                # Calculate career statistics
                years = sorted(year_counts.keys())
                first_year = min(years)
                last_year = max(years)
                career_length = last_year - first_year
                total_works = sum(year_counts.values())

                # Add one row per year to batch
                for year in years:
                    duck_batch_data.append((
                        author_id,
                        orcid,
                        display_name,
                        year,
                        year_counts[year],
                        total_works,
                        first_year,
                        last_year,
                        career_length
                    ))
                    total_author_work_records += 1

                authors_analyzed += 1

            # Write batch to DuckDB
            if duck_batch_data:
                duck_conn.executemany(
                    """INSERT INTO author_publications_by_year
                       (author_id, orcid, display_name, publication_year, works_count,
                        total_career_works, first_pub_year, last_pub_year, career_length_years)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    duck_batch_data
                )

            # Log progress after each batch
            elapsed = (datetime.now() - start_time).total_seconds()
            rate = authors_analyzed / elapsed if elapsed > 0 else 0
            pct_complete = (batch_end / len(authors)) * 100

            logger.info(
                f"Progress: {batch_end}/{len(authors)} authors ({pct_complete:.1f}%) | "
                f"Rate: {rate:.1f} authors/sec | "
                f"Records written: {total_author_work_records:,} | "
                f"Elapsed: {elapsed:.0f}s"
            )

        # Close database connections
        pg_cursor.close()
        pg_conn.close()
        duck_conn.close()
        logger.info("Database connections closed")

        # Final statistics
        total_elapsed = (datetime.now() - start_time).total_seconds()
        avg_rate = authors_analyzed / total_elapsed if total_elapsed > 0 else 0

        logger.info("="*70)
        logger.info("ANALYSIS COMPLETE")
        logger.info("="*70)
        logger.info(f"Authors analyzed: {authors_analyzed:,}")
        logger.info(f"Total author-year records written: {total_author_work_records:,}")
        logger.info(f"Total time: {total_elapsed:.2f} seconds")
        logger.info(f"Average rate: {avg_rate:.1f} authors/sec")
        logger.info(f"Output file: {output_file}")
        logger.info("="*70)

        return output_file, authors_analyzed

    except psycopg2.Error as e:
        logger.error(f"PostgreSQL error: {e}")
        raise
    except duckdb.Error as e:
        logger.error(f"DuckDB error: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise


def main():
    """
    Main entry point for the script.

    Parses command line arguments and initiates the analysis.
    """
    parser = argparse.ArgumentParser(
        description='Analyze publication patterns for random authors with ORCID IDs.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze 100,000 random authors (default)
  python 09_analyze_publications_by_year.py

  # Analyze 1,000 random authors for testing
  python 09_analyze_publications_by_year.py --sample-size 1000

  # Analyze authors with at least 10 works
  python 09_analyze_publications_by_year.py --min-works 10

  # Analyze with custom output filename
  python 09_analyze_publications_by_year.py --output my_analysis.duckdb
        """
    )

    parser.add_argument(
        '--sample-size',
        type=int,
        default=100000,
        help='Number of random authors to analyze (default: 100000)'
    )

    parser.add_argument(
        '--min-works',
        type=int,
        default=10,
        help='Minimum number of works to filter authors (default: 10)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='Custom output DuckDB filename (default: auto-generated with timestamp)'
    )

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging()

    logger.info("="*70)
    logger.info("AUTHOR PUBLICATION PATTERN ANALYSIS")
    logger.info("="*70)
    logger.info(f"Sample size: {args.sample_size} authors")
    logger.info(f"Filter: ORCID NOT NULL AND works_count > {args.min_works}")
    logger.info(f"Batch size: 100 authors per query")
    logger.info(f"Output format: DuckDB")
    logger.info(f"Output filename: {args.output if args.output else 'auto-generated'}")
    logger.info("="*70)

    try:
        # Run analysis
        output_file, total_authors = analyze_publication_patterns(
            sample_size=args.sample_size,
            min_works=args.min_works,
            output_filename=args.output
        )

        if total_authors > 0:
            logger.info("Script completed successfully")
            return 0
        else:
            logger.warning("No authors were analyzed")
            return 1

    except Exception as e:
        logger.critical(f"Script failed with error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())

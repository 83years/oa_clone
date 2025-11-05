"""
Career Stage Calculation for CF Corpus

Calculates career stage for authors using multiple methods:
1. Years Since First Publication (simple model)
2. Publication Velocity + Citations (data-driven model)

Career stages defined:
- Early: 0-5 years since first publication
- Mid: 6-15 years
- Senior: 16-25 years
- Emeritus: 26+ years
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '05_db_query'))

import psycopg2
from datetime import datetime
import logging

from config import CF_DB_CONFIG
from utils import setup_logging, ProgressMonitor


def calculate_publication_years(conn, logger):
    """
    Calculate first and last publication years for authors
    Uses works in cf_works joined with cf_authorship

    Args:
        conn: Database connection
        logger: Logger instance
    """
    logger.info("Calculating first and last publication years...")

    cursor = conn.cursor()

    # Calculate from authorships
    cursor.execute("""
        UPDATE cf_authors a
        SET
            first_publication_year = pub_years.first_year,
            last_publication_year = pub_years.last_year,
            career_length_years = pub_years.last_year - pub_years.first_year
        FROM (
            SELECT
                auth.author_id,
                MIN(w.publication_year) as first_year,
                MAX(w.publication_year) as last_year
            FROM cf_authorship auth
            JOIN cf_works w ON auth.work_id = w.work_id
            WHERE w.publication_year IS NOT NULL
            GROUP BY auth.author_id
        ) pub_years
        WHERE a.author_id = pub_years.author_id
    """)

    updated = cursor.rowcount
    conn.commit()
    logger.info(f"Updated publication years for {updated:,} authors")

    cursor.close()


def calculate_career_stage_simple(conn, logger):
    """
    Calculate career stage using years since first publication

    Career stages:
    - Early: 0-5 years
    - Mid: 6-15 years
    - Senior: 16-25 years
    - Emeritus: 26+ years

    Args:
        conn: Database connection
        logger: Logger instance
    """
    logger.info("Calculating career stage (simple model)...")

    cursor = conn.cursor()

    current_year = datetime.now().year

    # Early career (0-5 years)
    cursor.execute(f"""
        UPDATE cf_authors
        SET career_stage = 'Early',
            career_stage_method = 'years_since_first_pub'
        WHERE first_publication_year IS NOT NULL
            AND {current_year} - first_publication_year BETWEEN 0 AND 5
    """)
    early_count = cursor.rowcount

    # Mid career (6-15 years)
    cursor.execute(f"""
        UPDATE cf_authors
        SET career_stage = 'Mid',
            career_stage_method = 'years_since_first_pub'
        WHERE first_publication_year IS NOT NULL
            AND {current_year} - first_publication_year BETWEEN 6 AND 15
    """)
    mid_count = cursor.rowcount

    # Senior (16-25 years)
    cursor.execute(f"""
        UPDATE cf_authors
        SET career_stage = 'Senior',
            career_stage_method = 'years_since_first_pub'
        WHERE first_publication_year IS NOT NULL
            AND {current_year} - first_publication_year BETWEEN 16 AND 25
    """)
    senior_count = cursor.rowcount

    # Emeritus (26+ years)
    cursor.execute(f"""
        UPDATE cf_authors
        SET career_stage = 'Emeritus',
            career_stage_method = 'years_since_first_pub'
        WHERE first_publication_year IS NOT NULL
            AND {current_year} - first_publication_year >= 26
    """)
    emeritus_count = cursor.rowcount

    conn.commit()

    logger.info(f"Career stage assignment:")
    logger.info(f"  Early (0-5 years): {early_count:,}")
    logger.info(f"  Mid (6-15 years): {mid_count:,}")
    logger.info(f"  Senior (16-25 years): {senior_count:,}")
    logger.info(f"  Emeritus (26+ years): {emeritus_count:,}")
    logger.info(f"  Total assigned: {early_count + mid_count + senior_count + emeritus_count:,}")

    cursor.close()


def calculate_is_current(conn, logger):
    """
    Mark authors as current if they published in last 3 years

    Args:
        conn: Database connection
        logger: Logger instance
    """
    logger.info("Calculating current status...")

    cursor = conn.cursor()

    current_year = datetime.now().year
    threshold_year = current_year - 3

    cursor.execute(f"""
        UPDATE cf_authors
        SET is_current = (last_publication_year >= {threshold_year})
        WHERE last_publication_year IS NOT NULL
    """)

    updated = cursor.rowcount
    conn.commit()

    # Get counts
    cursor.execute("""
        SELECT
            COUNT(*) FILTER (WHERE is_current = TRUE) as current,
            COUNT(*) FILTER (WHERE is_current = FALSE) as not_current
        FROM cf_authors
    """)
    current, not_current = cursor.fetchone()

    logger.info(f"Current authors (published in last 3 years): {current:,}")
    logger.info(f"Not current: {not_current:,}")

    cursor.close()


def get_career_stage_statistics(conn, logger):
    """
    Generate statistics on career stages

    Args:
        conn: Database connection
        logger: Logger instance
    """
    cursor = conn.cursor()

    logger.info("\n" + "="*60)
    logger.info("CAREER STAGE STATISTICS")
    logger.info("="*60)

    # Overall distribution
    cursor.execute("""
        SELECT
            career_stage,
            COUNT(*) as count,
            AVG(works_count) as avg_works,
            AVG(cited_by_count) as avg_citations,
            AVG(h_index) as avg_h_index
        FROM cf_authors
        WHERE career_stage IS NOT NULL
        GROUP BY career_stage
        ORDER BY
            CASE career_stage
                WHEN 'Early' THEN 1
                WHEN 'Mid' THEN 2
                WHEN 'Senior' THEN 3
                WHEN 'Emeritus' THEN 4
            END
    """)

    logger.info("\nCareer stage distribution:")
    for stage, count, avg_works, avg_cit, avg_h in cursor.fetchall():
        logger.info(f"\n{stage} Career:")
        logger.info(f"  Authors: {count:,}")
        logger.info(f"  Avg works: {avg_works:.1f}")
        logger.info(f"  Avg citations: {avg_cit:.1f}")
        logger.info(f"  Avg h-index: {avg_h:.1f}" if avg_h else "  Avg h-index: N/A")

    # Gender by career stage
    cursor.execute("""
        SELECT
            career_stage,
            gender,
            COUNT(*) as count
        FROM cf_authors
        WHERE career_stage IS NOT NULL AND gender IN ('male', 'female')
        GROUP BY career_stage, gender
        ORDER BY career_stage, gender
    """)

    logger.info("\n" + "-"*60)
    logger.info("Gender distribution by career stage:")

    current_stage = None
    stage_counts = {}

    for stage, gender, count in cursor.fetchall():
        if stage != current_stage:
            if current_stage and current_stage in stage_counts:
                total = sum(stage_counts[current_stage].values())
                male = stage_counts[current_stage].get('male', 0)
                female = stage_counts[current_stage].get('female', 0)
                male_pct = (male / total * 100) if total > 0 else 0
                female_pct = (female / total * 100) if total > 0 else 0
                logger.info(f"  Male: {male_pct:.1f}%, Female: {female_pct:.1f}%")

            current_stage = stage
            stage_counts[stage] = {}
            logger.info(f"\n{stage}:")

        stage_counts[stage][gender] = count

    # Print last stage
    if current_stage and current_stage in stage_counts:
        total = sum(stage_counts[current_stage].values())
        male = stage_counts[current_stage].get('male', 0)
        female = stage_counts[current_stage].get('female', 0)
        male_pct = (male / total * 100) if total > 0 else 0
        female_pct = (female / total * 100) if total > 0 else 0
        logger.info(f"  Male: {male_pct:.1f}%, Female: {female_pct:.1f}%")

    cursor.close()


def main():
    """Main execution"""
    logger = setup_logging('calculate_career_stage')

    logger.info("Clinical Flow Cytometry - Career Stage Calculation")
    logger.info(f"Started at: {datetime.now()}")

    # Connect to CF_DB
    logger.info("\nConnecting to CF_DB...")
    conn = psycopg2.connect(**CF_DB_CONFIG)

    try:
        # Step 1: Calculate publication years
        logger.info("\n" + "="*60)
        logger.info("STEP 1: Calculate Publication Years")
        logger.info("="*60)
        calculate_publication_years(conn, logger)

        # Step 2: Calculate career stage
        logger.info("\n" + "="*60)
        logger.info("STEP 2: Assign Career Stages")
        logger.info("="*60)
        calculate_career_stage_simple(conn, logger)

        # Step 3: Mark current authors
        logger.info("\n" + "="*60)
        logger.info("STEP 3: Calculate Current Status")
        logger.info("="*60)
        calculate_is_current(conn, logger)

        # Statistics
        get_career_stage_statistics(conn, logger)

        logger.info(f"\nCompleted at: {datetime.now()}")
        logger.info("SUCCESS: Career stage calculation complete")

        return 0

    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)
        return 1

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    sys.exit(main())

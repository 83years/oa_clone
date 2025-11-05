"""
Build Complete Author Profiles

Calculates all derived metrics for author profiles:
- Authorship frequencies (corresponding, first, last)
- Most cited work and max citations
- Primary topic and concept

This completes the author profile construction.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '05_db_query'))

import psycopg2
from datetime import datetime

from config import CF_DB_CONFIG
from utils import setup_logging


def calculate_authorship_frequencies(conn, logger):
    """
    Calculate authorship position frequencies

    Args:
        conn: Database connection
        logger: Logger instance
    """
    logger.info("Calculating authorship frequencies...")

    cursor = conn.cursor()

    # Calculate counts and frequencies
    cursor.execute("""
        UPDATE cf_authors a
        SET
            corresponding_authorships = auth_stats.corresponding_count,
            first_authorships = auth_stats.first_count,
            last_authorships = auth_stats.last_count,
            freq_corresponding_author = auth_stats.corresponding_count::float / NULLIF(a.works_count, 0),
            freq_first_author = auth_stats.first_count::float / NULLIF(a.works_count, 0),
            freq_last_author = auth_stats.last_count::float / NULLIF(a.works_count, 0)
        FROM (
            SELECT
                author_id,
                COUNT(*) FILTER (WHERE is_corresponding = TRUE) as corresponding_count,
                COUNT(*) FILTER (WHERE author_position = 'first') as first_count,
                COUNT(*) FILTER (WHERE author_position = 'last') as last_count
            FROM cf_authorship
            GROUP BY author_id
        ) auth_stats
        WHERE a.author_id = auth_stats.author_id
    """)

    updated = cursor.rowcount
    conn.commit()
    logger.info(f"Updated authorship frequencies for {updated:,} authors")

    cursor.close()


def calculate_most_cited_work(conn, logger):
    """
    Find most cited work for each author

    Args:
        conn: Database connection
        logger: Logger instance
    """
    logger.info("Calculating most cited works...")

    cursor = conn.cursor()

    cursor.execute("""
        UPDATE cf_authors a
        SET
            most_cited_work = cited_works.work_id,
            max_citations = cited_works.max_cit
        FROM (
            SELECT DISTINCT ON (auth.author_id)
                auth.author_id,
                w.work_id,
                w.cited_by_count as max_cit
            FROM cf_authorship auth
            JOIN cf_works w ON auth.work_id = w.work_id
            ORDER BY auth.author_id, w.cited_by_count DESC
        ) cited_works
        WHERE a.author_id = cited_works.author_id
    """)

    updated = cursor.rowcount
    conn.commit()
    logger.info(f"Updated most cited work for {updated:,} authors")

    cursor.close()


def calculate_primary_topic(conn, logger):
    """
    Determine primary research topic for each author
    Based on most common topic across their works

    Args:
        conn: Database connection
        logger: Logger instance
    """
    logger.info("Calculating primary topics...")

    cursor = conn.cursor()

    # First, ensure cf_topics table is populated
    cursor.execute("SELECT COUNT(*) FROM cf_topics")
    topic_count = cursor.fetchone()[0]

    if topic_count == 0:
        logger.warning("cf_topics table is empty - skipping primary topic calculation")
        logger.info("Run topic extraction from works first if needed")
        cursor.close()
        return

    # Calculate primary topic
    cursor.execute("""
        UPDATE cf_authors a
        SET
            primary_topic_id = author_topics.topic_id,
            primary_topic_name = t.display_name
        FROM (
            SELECT DISTINCT ON (auth.author_id)
                auth.author_id,
                wt.topic_id,
                COUNT(*) as topic_count
            FROM cf_authorship auth
            JOIN cf_work_topics wt ON auth.work_id = wt.work_id
            GROUP BY auth.author_id, wt.topic_id
            ORDER BY auth.author_id, COUNT(*) DESC
        ) author_topics
        LEFT JOIN cf_topics t ON author_topics.topic_id = t.topic_id
        WHERE a.author_id = author_topics.author_id
    """)

    updated = cursor.rowcount
    conn.commit()
    logger.info(f"Updated primary topic for {updated:,} authors")

    cursor.close()


def calculate_primary_concept(conn, logger):
    """
    Determine primary concept for each author
    Based on highest average score across their works

    Args:
        conn: Database connection
        logger: Logger instance
    """
    logger.info("Calculating primary concepts...")

    cursor = conn.cursor()

    # Check if concepts exist
    cursor.execute("SELECT COUNT(*) FROM cf_concepts")
    concept_count = cursor.fetchone()[0]

    if concept_count == 0:
        logger.warning("cf_concepts table is empty - skipping primary concept calculation")
        cursor.close()
        return

    # Calculate primary concept
    cursor.execute("""
        UPDATE cf_authors a
        SET
            primary_concept_id = author_concepts.concept_id,
            primary_concept_name = c.display_name
        FROM (
            SELECT DISTINCT ON (auth.author_id)
                auth.author_id,
                wc.concept_id,
                AVG(wc.score) as avg_score
            FROM cf_authorship auth
            JOIN cf_work_concepts wc ON auth.work_id = wc.work_id
            GROUP BY auth.author_id, wc.concept_id
            ORDER BY auth.author_id, AVG(wc.score) DESC
        ) author_concepts
        LEFT JOIN cf_concepts c ON author_concepts.concept_id = c.concept_id
        WHERE a.author_id = author_concepts.author_id
    """)

    updated = cursor.rowcount
    conn.commit()
    logger.info(f"Updated primary concept for {updated:,} authors")

    cursor.close()


def get_profile_statistics(conn, logger):
    """
    Generate statistics on completed profiles

    Args:
        conn: Database connection
        logger: Logger instance
    """
    cursor = conn.cursor()

    logger.info("\n" + "="*60)
    logger.info("AUTHOR PROFILE STATISTICS")
    logger.info("="*60)

    # Completeness metrics
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(gender) FILTER (WHERE gender != 'unknown') as with_gender,
            COUNT(career_stage) as with_career_stage,
            COUNT(freq_corresponding_author) as with_authorship_freq,
            COUNT(most_cited_work) as with_most_cited,
            COUNT(primary_topic_id) as with_primary_topic
        FROM cf_authors
    """)

    total, with_gender, with_stage, with_freq, with_cited, with_topic = cursor.fetchone()

    logger.info(f"Total authors: {total:,}")
    logger.info(f"\nProfile completeness:")
    logger.info(f"  Gender assigned: {with_gender:,} ({with_gender/total*100:.1f}%)")
    logger.info(f"  Career stage: {with_stage:,} ({with_stage/total*100:.1f}%)")
    logger.info(f"  Authorship frequencies: {with_freq:,} ({with_freq/total*100:.1f}%)")
    logger.info(f"  Most cited work: {with_cited:,} ({with_cited/total*100:.1f}%)")
    logger.info(f"  Primary topic: {with_topic:,} ({with_topic/total*100:.1f}%)")

    # Authorship patterns
    cursor.execute("""
        SELECT
            AVG(freq_corresponding_author) as avg_corresponding,
            AVG(freq_first_author) as avg_first,
            AVG(freq_last_author) as avg_last
        FROM cf_authors
        WHERE freq_corresponding_author IS NOT NULL
    """)

    avg_corr, avg_first, avg_last = cursor.fetchone()

    logger.info(f"\nAverage authorship frequencies:")
    logger.info(f"  Corresponding: {avg_corr*100:.1f}%")
    logger.info(f"  First author: {avg_first*100:.1f}%")
    logger.info(f"  Last author: {avg_last*100:.1f}%")

    # Gender differences in authorship patterns
    cursor.execute("""
        SELECT
            gender,
            AVG(freq_corresponding_author) as avg_corresponding,
            AVG(freq_first_author) as avg_first,
            AVG(freq_last_author) as avg_last,
            COUNT(*) as count
        FROM cf_authors
        WHERE gender IN ('male', 'female')
            AND freq_corresponding_author IS NOT NULL
        GROUP BY gender
    """)

    logger.info(f"\nAuthorship patterns by gender:")
    for gender, avg_corr, avg_first, avg_last, count in cursor.fetchall():
        logger.info(f"\n{gender.capitalize()} (n={count:,}):")
        logger.info(f"  Corresponding: {avg_corr*100:.1f}%")
        logger.info(f"  First author: {avg_first*100:.1f}%")
        logger.info(f"  Last author: {avg_last*100:.1f}%")

    # Top primary topics
    logger.info(f"\nTop 10 primary topics:")
    cursor.execute("""
        SELECT primary_topic_name, COUNT(*) as count
        FROM cf_authors
        WHERE primary_topic_name IS NOT NULL
        GROUP BY primary_topic_name
        ORDER BY COUNT(*) DESC
        LIMIT 10
    """)

    for topic, count in cursor.fetchall():
        logger.info(f"  {topic}: {count:,} authors")

    cursor.close()


def main():
    """Main execution"""
    logger = setup_logging('build_author_profiles')

    logger.info("Clinical Flow Cytometry - Build Author Profiles")
    logger.info(f"Started at: {datetime.now()}")

    # Connect to CF_DB
    logger.info("\nConnecting to CF_DB...")
    conn = psycopg2.connect(**CF_DB_CONFIG)

    try:
        # Step 1: Authorship frequencies
        logger.info("\n" + "="*60)
        logger.info("STEP 1: Calculate Authorship Frequencies")
        logger.info("="*60)
        calculate_authorship_frequencies(conn, logger)

        # Step 2: Most cited work
        logger.info("\n" + "="*60)
        logger.info("STEP 2: Identify Most Cited Works")
        logger.info("="*60)
        calculate_most_cited_work(conn, logger)

        # Step 3: Primary topic
        logger.info("\n" + "="*60)
        logger.info("STEP 3: Determine Primary Topics")
        logger.info("="*60)
        calculate_primary_topic(conn, logger)

        # Step 4: Primary concept
        logger.info("\n" + "="*60)
        logger.info("STEP 4: Determine Primary Concepts")
        logger.info("="*60)
        calculate_primary_concept(conn, logger)

        # Statistics
        get_profile_statistics(conn, logger)

        logger.info(f"\nCompleted at: {datetime.now()}")
        logger.info("SUCCESS: Author profiles complete")

        return 0

    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)
        return 1

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    sys.exit(main())

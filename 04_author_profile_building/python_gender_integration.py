"""
Python Gender Integration for CF Corpus

Predicts gender for authors in the CF corpus using a multi-method approach:
1. gender-guesser Python package (primary, works offline)
2. Genderize.io API (fallback for unknowns, requires API key)

Country-aware predictions improve accuracy.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '05_db_query'))

import psycopg2
import gender_guesser.detector as gender
from datetime import datetime
import logging
import time
from typing import Dict, Optional, Tuple

# Import from Phase 5
from config import CF_DB_CONFIG
from utils import setup_logging, ProgressMonitor


class GenderPredictor:
    """Multi-method gender prediction"""

    def __init__(self, logger):
        self.logger = logger
        self.detector = gender.Detector(case_sensitive=False)
        self.stats = {
            'total': 0,
            'male': 0,
            'female': 0,
            'unknown': 0,
            'andy': 0,  # androgynous
            'method_guesser': 0,
            'method_api': 0
        }

    def predict_from_name(self, first_name: str, country: str = None) -> Tuple[str, str, float]:
        """
        Predict gender from first name

        Args:
            first_name: Author's first name
            country: ISO country code (improves accuracy)

        Returns:
            Tuple of (gender, method, confidence)
            gender: 'male', 'female', 'unknown'
            method: 'gender-guesser' or 'api'
            confidence: 0.0-1.0
        """
        if not first_name:
            return ('unknown', 'none', 0.0)

        # Clean name (remove middle initials, etc.)
        name_parts = first_name.strip().split()
        first_name_clean = name_parts[0] if name_parts else first_name

        # Try gender-guesser
        if country:
            result = self.detector.get_gender(first_name_clean, country)
        else:
            result = self.detector.get_gender(first_name_clean)

        # Map results
        gender_map = {
            'male': ('male', 1.0),
            'female': ('female', 1.0),
            'mostly_male': ('male', 0.75),
            'mostly_female': ('female', 0.75),
            'andy': ('unknown', 0.0),
            'unknown': ('unknown', 0.0)
        }

        mapped_gender, confidence = gender_map.get(result, ('unknown', 0.0))

        if mapped_gender != 'unknown':
            self.stats['method_guesser'] += 1
            return (mapped_gender, 'gender-guesser', confidence)

        # Could add Genderize.io API here as fallback
        # For now, return unknown
        return ('unknown', 'none', 0.0)

    def update_stats(self, gender: str):
        """Update prediction statistics"""
        self.stats['total'] += 1
        if gender == 'male':
            self.stats['male'] += 1
        elif gender == 'female':
            self.stats['female'] += 1
        elif gender == 'unknown':
            self.stats['unknown'] += 1
        else:
            self.stats['andy'] += 1

    def get_stats(self) -> Dict:
        """Get prediction statistics"""
        total = self.stats['total']
        if total == 0:
            return self.stats

        return {
            **self.stats,
            'male_pct': (self.stats['male'] / total) * 100,
            'female_pct': (self.stats['female'] / total) * 100,
            'unknown_pct': (self.stats['unknown'] / total) * 100,
            'coverage': ((total - self.stats['unknown']) / total) * 100 if total > 0 else 0
        }


def extract_first_name(display_name: str) -> str:
    """
    Extract first name from display name

    Args:
        display_name: Full author name

    Returns:
        First name

    Examples:
        "John Smith" -> "John"
        "Smith, John" -> "John"
        "J. Smith" -> "J"
    """
    if not display_name:
        return None

    # Handle "Last, First" format
    if ',' in display_name:
        parts = display_name.split(',')
        first_part = parts[1].strip() if len(parts) > 1 else parts[0].strip()
    else:
        # Handle "First Last" format
        first_part = display_name.strip()

    # Get first word
    words = first_part.split()
    first_name = words[0] if words else None

    # Remove periods (for initials)
    if first_name:
        first_name = first_name.replace('.', '').strip()

    return first_name


def fetch_authors_without_gender(conn, logger):
    """
    Get authors from CF_DB who don't have gender assigned

    Args:
        conn: Database connection
        logger: Logger instance

    Returns:
        List of author tuples (author_id, display_name, country)
    """
    cursor = conn.cursor()

    cursor.execute("""
        SELECT author_id, display_name, current_affiliation_country
        FROM cf_authors
        WHERE gender IS NULL
        ORDER BY author_id
    """)

    authors = cursor.fetchall()
    logger.info(f"Found {len(authors)} authors without gender assigned")

    cursor.close()
    return authors


def predict_and_store_genders(conn, authors, logger):
    """
    Predict genders for all authors and update database

    Args:
        conn: Database connection
        authors: List of author tuples
        logger: Logger instance
    """
    if not authors:
        logger.info("No authors to process")
        return

    predictor = GenderPredictor(logger)
    monitor = ProgressMonitor(logger, total=len(authors), report_interval=1000)

    # Batch updates
    batch = []
    batch_size = 1000

    logger.info(f"Predicting genders for {len(authors)} authors...")

    for author_id, display_name, country in authors:
        try:
            # Extract first name
            first_name = extract_first_name(display_name)

            # Predict gender
            gender_pred, method, confidence = predictor.predict_from_name(first_name, country)

            # Update stats
            predictor.update_stats(gender_pred)

            # Add to batch
            batch.append((gender_pred, method, confidence, author_id))

            # Write batch when full
            if len(batch) >= batch_size:
                write_gender_batch(conn, batch, logger)
                batch = []

            monitor.update()

        except Exception as e:
            logger.error(f"Error processing author {author_id}: {e}")
            continue

    # Write remaining batch
    if batch:
        write_gender_batch(conn, batch, logger)

    monitor.final_report()

    # Print statistics
    stats = predictor.get_stats()
    logger.info("\n" + "="*60)
    logger.info("GENDER PREDICTION STATISTICS")
    logger.info("="*60)
    logger.info(f"Total processed: {stats['total']:,}")
    logger.info(f"Male: {stats['male']:,} ({stats.get('male_pct', 0):.1f}%)")
    logger.info(f"Female: {stats['female']:,} ({stats.get('female_pct', 0):.1f}%)")
    logger.info(f"Unknown: {stats['unknown']:,} ({stats.get('unknown_pct', 0):.1f}%)")
    logger.info(f"Coverage: {stats.get('coverage', 0):.1f}%")
    logger.info(f"\nMethod breakdown:")
    logger.info(f"  gender-guesser: {stats['method_guesser']:,}")


def write_gender_batch(conn, batch, logger):
    """
    Write batch of gender predictions to database

    Args:
        conn: Database connection
        batch: List of tuples (gender, method, confidence, author_id)
        logger: Logger instance
    """
    try:
        cursor = conn.cursor()

        cursor.executemany("""
            UPDATE cf_authors
            SET gender = %s,
                gender_method = %s,
                gender_confidence = %s
            WHERE author_id = %s
        """, batch)

        conn.commit()
        logger.debug(f"Updated {len(batch)} author gender predictions")
        cursor.close()

    except Exception as e:
        logger.error(f"Error writing gender batch: {e}")
        conn.rollback()
        raise


def get_gender_statistics(conn, logger):
    """
    Get overall gender statistics from database

    Args:
        conn: Database connection
        logger: Logger instance
    """
    cursor = conn.cursor()

    logger.info("\n" + "="*60)
    logger.info("CORPUS GENDER STATISTICS")
    logger.info("="*60)

    # Overall counts
    cursor.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE gender = 'male') as male,
            COUNT(*) FILTER (WHERE gender = 'female') as female,
            COUNT(*) FILTER (WHERE gender = 'unknown' OR gender IS NULL) as unknown
        FROM cf_authors
    """)

    total, male, female, unknown = cursor.fetchone()

    logger.info(f"Total authors: {total:,}")
    logger.info(f"Male: {male:,} ({male/total*100:.1f}%)")
    logger.info(f"Female: {female:,} ({female/total*100:.1f}%)")
    logger.info(f"Unknown: {unknown:,} ({unknown/total*100:.1f}%)")

    # By country (top 10)
    cursor.execute("""
        SELECT
            current_affiliation_country,
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE gender = 'male') as male,
            COUNT(*) FILTER (WHERE gender = 'female') as female
        FROM cf_authors
        WHERE current_affiliation_country IS NOT NULL
            AND gender IN ('male', 'female')
        GROUP BY current_affiliation_country
        ORDER BY COUNT(*) DESC
        LIMIT 10
    """)

    logger.info("\nGender distribution by country (top 10):")
    for country, total, male, female in cursor.fetchall():
        male_pct = (male / total * 100) if total > 0 else 0
        female_pct = (female / total * 100) if total > 0 else 0
        logger.info(f"  {country}: M={male_pct:.1f}% F={female_pct:.1f}% (n={total})")

    cursor.close()


def main():
    """Main execution"""
    logger = setup_logging('python_gender_integration')

    logger.info("Clinical Flow Cytometry - Gender Prediction")
    logger.info(f"Started at: {datetime.now()}")

    # Check if gender-guesser is installed
    try:
        import gender_guesser.detector
    except ImportError:
        logger.error("gender-guesser package not found!")
        logger.error("Install with: pip install gender-guesser")
        return 1

    # Connect to CF_DB
    logger.info("\nConnecting to CF_DB...")
    conn = psycopg2.connect(**CF_DB_CONFIG)

    try:
        # Fetch authors without gender
        logger.info("\n" + "="*60)
        logger.info("STEP 1: Fetch Authors Without Gender")
        logger.info("="*60)
        authors = fetch_authors_without_gender(conn, logger)

        # Predict genders
        logger.info("\n" + "="*60)
        logger.info("STEP 2: Predict Genders")
        logger.info("="*60)
        predict_and_store_genders(conn, authors, logger)

        # Get statistics
        get_gender_statistics(conn, logger)

        logger.info(f"\nCompleted at: {datetime.now()}")
        logger.info("SUCCESS: Gender prediction complete")

        return 0

    except Exception as e:
        logger.error(f"Error during execution: {e}", exc_info=True)
        return 1

    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    sys.exit(main())

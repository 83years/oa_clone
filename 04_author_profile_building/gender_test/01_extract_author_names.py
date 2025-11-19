#!/usr/bin/env python3
"""
Step 1: Extract Author Names and Country Codes from PostgreSQL

This script:
1. Reads author_id and display_name from authors table
2. Reads author_id and alternative_name from author_name_variants table
3. Extracts country codes from institutions via author_institutions
4. Parses forenames from all names using advanced Unicode-aware parsing
5. Outputs JSON file with author_id, forename, country_code

Ported from R script with PostgreSQL support.
"""

import sys
import os
import re
import json
import logging
from datetime import datetime
from typing import Optional, Dict, List, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
from collections import Counter

# Add parent directory to path for config import
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import DB_CONFIG


# ==============================================================================
# CONFIGURATION
# ==============================================================================

class Config:
    """Configuration for name extraction"""
    # Database connection
    DB_CONFIG = DB_CONFIG

    # Feature flags
    USE_NAME_VARIANTS = True
    USE_COUNTRY_CONTEXT = True

    # Processing parameters
    BATCH_SIZE = 25000
    MIN_FORENAME_LENGTH = 2

    # Output paths
    OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'output')
    OUTPUT_FILE = os.path.join(OUTPUT_DIR, '01_extracted_names.json')

    # Logging
    LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
    LOG_FILE = os.path.join(LOG_DIR, f'01_extract_names_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')


# ==============================================================================
# LOGGING SETUP
# ==============================================================================

def setup_logging():
    """Initialize logging to console and file"""
    os.makedirs(Config.LOG_DIR, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.FileHandler(Config.LOG_FILE),
            logging.StreamHandler(sys.stdout)
        ]
    )

    logging.info(f"Logging initialized: {Config.LOG_FILE}")


# ==============================================================================
# NAME PARSING FUNCTIONS
# ==============================================================================

def normalize_unicode_dashes(text: str) -> str:
    """Normalize various Unicode dashes to standard hyphen"""
    # Unicode dashes: U+2010 to U+2015
    dash_pattern = r'[\u2010-\u2015]'
    return re.sub(dash_pattern, '-', text)


def looks_like_initial(part: str) -> bool:
    """
    Detect if a name part looks like an initial

    Examples:
    - K. → True
    - J.R. → True
    - K.W.Pawar → True (detected elsewhere)
    - JOHN → True (if all caps and ≤4 chars)
    - Jean → False
    """
    # Remove periods and hyphens for checking
    clean_part = re.sub(r'[.\-]', '', part)

    # Single character
    if len(clean_part) == 1:
        return True

    # 1-2 chars with period (K., JR.)
    if len(clean_part) <= 2 and '.' in part:
        return True

    # All uppercase and ≤4 characters (J, JR, JRS, etc.)
    if len(clean_part) <= 4 and clean_part.isupper():
        return True

    # Pattern like A.-B or A.B
    if re.match(r'^[A-Z][.\-][A-Z]', part):
        return True

    return False


def parse_forename(display_name: Optional[str]) -> Optional[str]:
    """
    Advanced forename parsing with Unicode support

    Ported from R's parse_forename() function.

    Handles:
    - Compound names (Jean-François)
    - International characters (Latin, Cyrillic, CJK)
    - Initial detection (K.W.Pawar → NA)
    - Various name formats

    Args:
        display_name: Full author name

    Returns:
        Extracted forename or None if cannot parse
    """
    # Validation
    if not display_name or not isinstance(display_name, str):
        return None

    display_name = display_name.strip()

    if len(display_name) < 2:
        return None

    # Normalize Unicode dashes
    clean_name = normalize_unicode_dashes(display_name)

    # ===========================================================================
    # Case 1: Single word (no spaces)
    # ===========================================================================
    if ' ' not in clean_name:
        # Has periods?
        if '.' in clean_name:
            period_parts = clean_name.split('.')

            if len(period_parts) >= 2:
                first_part = period_parts[0].strip()

                # Likely initials (K., JR.)
                if len(first_part) <= 2:
                    return None

                # Valid name before period
                if len(first_part) >= 3:
                    return first_part

        # Has hyphens (compound names) but no periods?
        if '-' in clean_name and '.' not in clean_name:
            # Clean leading/trailing non-letters
            # Unicode range: Latin letters (A-Z, a-z, À-ÿ, Ā-ſ, Ơ-ɏ)
            compound_name = re.sub(r'^[^A-Za-z\u00C0-\u024F]+|[^A-Za-z\u00C0-\u024F-]+$', '', clean_name)

            if len(compound_name) >= 3:
                return compound_name

        # Single word with no special handling
        return None

    # ===========================================================================
    # Case 2: Space-separated format (most common)
    # ===========================================================================
    parts = [p for p in clean_name.split() if p]  # Split and remove empty

    if len(parts) < 2:
        return None

    first_part = parts[0]

    # Check if first part looks like an initial
    if looks_like_initial(first_part):
        return None

    # Clean extracted name (remove periods, trim)
    first_name = first_part.replace('.', '').strip()

    # ===========================================================================
    # Validation
    # ===========================================================================

    # Minimum length
    if len(first_name) < 2:
        return None

    # All uppercase and short (likely initials like JOHN → JN)
    if first_name.isupper() and len(first_name) <= 4:
        return None

    # Must contain only valid characters:
    # - Latin letters: A-Z, a-z
    # - Extended Latin: À-ÿ (U+00C0-U+00FF)
    # - Extended Latin: Ā-ſ (U+0100-U+017F)
    # - Extended Latin: Ơ-ɏ (U+0180-U+024F)
    # - Hyphens for compound names
    valid_chars_pattern = r'^[A-Za-z\u00C0-\u00FF\u0100-\u017F\u0180-\u024F-]+$'

    if not re.match(valid_chars_pattern, first_name):
        return None

    return first_name


# ==============================================================================
# DATABASE FUNCTIONS
# ==============================================================================

def create_db_connection() -> psycopg2.extensions.connection:
    """Create PostgreSQL database connection"""
    try:
        conn = psycopg2.connect(**Config.DB_CONFIG)
        logging.info(f"Connected to database: {Config.DB_CONFIG['database']}@{Config.DB_CONFIG['host']}")
        return conn
    except Exception as e:
        logging.error(f"Database connection failed: {e}")
        raise


def extract_authors(conn: psycopg2.extensions.connection) -> List[Dict]:
    """
    Extract authors and display names from database

    Returns:
        List of dicts with author_id and display_name
    """
    logging.info("Extracting authors and display names...")

    query = """
        SELECT
            author_id,
            display_name
        FROM authors
        WHERE display_name IS NOT NULL
          AND display_name != ''
    """

    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query)
        results = cursor.fetchall()

    # Convert to list of dicts
    authors = [dict(row) for row in results]

    logging.info(f"Loaded {len(authors):,} authors with display names")

    return authors


def extract_name_variants(conn: psycopg2.extensions.connection) -> List[Dict]:
    """
    Extract alternative names from author_name_variants table

    Returns:
        List of dicts with author_id and alternative_name
    """
    if not Config.USE_NAME_VARIANTS:
        logging.info("Name variants disabled in config")
        return []

    logging.info("Extracting author name variants...")

    # Check if table exists
    check_query = """
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'author_name_variants'
        )
    """

    with conn.cursor() as cursor:
        cursor.execute(check_query)
        table_exists = cursor.fetchone()[0]

    if not table_exists:
        logging.warning("Table 'author_name_variants' not found, skipping variants")
        return []

    query = """
        SELECT
            author_id,
            alternative_name
        FROM author_name_variants
        WHERE alternative_name IS NOT NULL
          AND alternative_name != ''
    """

    with conn.cursor(cursor_factory=RealDictCursor) as cursor:
        cursor.execute(query)
        results = cursor.fetchall()

    variants = [dict(row) for row in results]

    logging.info(f"Loaded {len(variants):,} name variants")

    return variants


def extract_country_codes(conn: psycopg2.extensions.connection) -> Dict[str, str]:
    """
    Extract country codes from institutions via author_institutions

    For authors with multiple countries, takes the most frequent.

    Returns:
        Dict mapping author_id to country_code
    """
    if not Config.USE_COUNTRY_CONTEXT:
        logging.info("Country context disabled in config")
        return {}

    logging.info("Extracting country codes from institutions...")

    # Check if tables exist
    check_query = """
        SELECT
            (SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'institutions')) as inst_exists,
            (SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'author_institutions')) as auth_inst_exists
    """

    with conn.cursor() as cursor:
        cursor.execute(check_query)
        inst_exists, auth_inst_exists = cursor.fetchone()

    if not (inst_exists and auth_inst_exists):
        logging.warning("Institution tables not found, skipping country extraction")
        return {}

    query = """
        SELECT DISTINCT
            ai.author_id,
            i.country_code
        FROM author_institutions AS ai
        INNER JOIN institutions AS i
          ON ai.institution_id = i.institution_id
        WHERE i.country_code IS NOT NULL
          AND i.country_code != ''
    """

    with conn.cursor() as cursor:
        cursor.execute(query)
        results = cursor.fetchall()

    logging.info(f"Loaded {len(results):,} author-country associations")

    # Handle authors with multiple countries - take most common
    author_countries = {}
    for author_id, country_code in results:
        if author_id not in author_countries:
            author_countries[author_id] = []
        author_countries[author_id].append(country_code)

    # Resolve to single country per author
    resolved = {}
    for author_id, countries in author_countries.items():
        if len(countries) == 1:
            resolved[author_id] = countries[0]
        else:
            # Take most frequent, alphabetically if tie
            counter = Counter(countries)
            most_common = counter.most_common()
            max_count = most_common[0][1]

            # Get all countries with max count and sort alphabetically
            top_countries = sorted([c for c, count in most_common if count == max_count])
            resolved[author_id] = top_countries[0]

    logging.info(f"Resolved to {len(resolved):,} unique author-country pairs")

    return resolved


# ==============================================================================
# MAIN EXTRACTION FUNCTION
# ==============================================================================

def extract_author_names() -> List[Dict]:
    """
    Main extraction function

    Returns:
        List of dicts with author_id, forename, country_code
    """
    logging.info("=== STEP 1: EXTRACT AUTHOR NAMES ===")

    conn = create_db_connection()

    try:
        # ======================================================================
        # Extract data from database
        # ======================================================================
        authors = extract_authors(conn)
        variants = extract_name_variants(conn)
        country_codes = extract_country_codes(conn)

        # ======================================================================
        # Combine all names (display_name + variants)
        # ======================================================================
        logging.info("Combining display names and variants...")

        all_names = []

        # Add display names
        for author in authors:
            all_names.append({
                'author_id': author['author_id'],
                'name': author['display_name'],
                'source': 'display_name'
            })

        # Add variants
        for variant in variants:
            all_names.append({
                'author_id': variant['author_id'],
                'name': variant['alternative_name'],
                'source': 'variant'
            })

        logging.info(f"Total names to process: {len(all_names):,}")

        # ======================================================================
        # Parse forenames in batches
        # ======================================================================
        logging.info("Parsing forenames from names...")

        batch_size = Config.BATCH_SIZE
        total_names = len(all_names)
        num_batches = (total_names + batch_size - 1) // batch_size  # Ceiling division

        logging.info(f"Processing in {num_batches} batches of {batch_size:,}")

        parsed_names = []
        successful_parses = 0

        for batch_num in range(num_batches):
            start_idx = batch_num * batch_size
            end_idx = min((batch_num + 1) * batch_size, total_names)

            current_batch = all_names[start_idx:end_idx]

            # Parse forenames
            for record in current_batch:
                forename = parse_forename(record['name'])

                if forename:
                    parsed_names.append({
                        'author_id': record['author_id'],
                        'forename': forename,
                        'source': record['source']
                    })
                    successful_parses += 1

            # Progress reporting
            if (batch_num + 1) % 10 == 0 or batch_num == num_batches - 1:
                success_rate = (successful_parses / end_idx * 100) if end_idx > 0 else 0
                logging.info(f"Batch {batch_num + 1}/{num_batches} - Success rate: {success_rate:.2f}%")

        logging.info(f"Successfully parsed {len(parsed_names):,} forenames")

        # ======================================================================
        # Deduplicate: prioritize display_name over variants
        # ======================================================================
        logging.info("Deduplicating names...")

        # Sort by source priority (display_name before variant)
        source_priority = {'display_name': 0, 'variant': 1}
        parsed_names.sort(key=lambda x: (x['author_id'], source_priority[x['source']], x['forename']))

        # Keep first occurrence per author-forename pair
        seen = set()
        unique_names = []

        for record in parsed_names:
            key = (record['author_id'], record['forename'])
            if key not in seen:
                seen.add(key)
                unique_names.append({
                    'author_id': record['author_id'],
                    'forename': record['forename']
                })

        logging.info(f"Unique author-forename combinations: {len(unique_names):,}")

        # ======================================================================
        # Join with country codes
        # ======================================================================
        if country_codes:
            logging.info("Joining with country codes...")

            with_country = 0
            without_country = 0

            for record in unique_names:
                country_code = country_codes.get(record['author_id'])
                record['country_code'] = country_code

                if country_code:
                    with_country += 1
                else:
                    without_country += 1

            logging.info(f"Authors with country code: {with_country:,}")
            logging.info(f"Authors without country code: {without_country:,}")
        else:
            for record in unique_names:
                record['country_code'] = None
            logging.info("No country codes available")

        # ======================================================================
        # Add metadata and filter by minimum length
        # ======================================================================
        final_data = []

        for record in unique_names:
            if len(record['forename']) >= Config.MIN_FORENAME_LENGTH:
                record['extraction_date'] = datetime.now().strftime('%Y-%m-%d')
                record['min_forename_length'] = Config.MIN_FORENAME_LENGTH
                final_data.append(record)

        logging.info(f"Final dataset size: {len(final_data):,} records")

        # ======================================================================
        # Generate summary statistics
        # ======================================================================
        logging.info("\n=== EXTRACTION SUMMARY ===")
        logging.info(f"Total authors processed: {len(authors):,}")

        if variants:
            logging.info(f"Name variants processed: {len(variants):,}")

        logging.info(f"Total names parsed: {len(parsed_names):,}")
        logging.info(f"Unique author-forename pairs: {len(unique_names):,}")
        logging.info(f"Final records (after filtering): {len(final_data):,}")

        if country_codes:
            coverage = (with_country / len(final_data) * 100) if final_data else 0
            logging.info(f"Country code coverage: {coverage:.2f}%")

        # Forename length distribution
        length_bins = [(2, 3), (4, 5), (6, 8), (9, 15), (16, float('inf'))]
        length_labels = ["2-3", "4-5", "6-8", "9-15", "15+"]
        length_dist = {label: 0 for label in length_labels}

        for record in final_data:
            name_len = len(record['forename'])
            for (min_len, max_len), label in zip(length_bins, length_labels):
                if min_len <= name_len <= max_len:
                    length_dist[label] += 1
                    break

        logging.info("\nForename length distribution:")
        for label, count in length_dist.items():
            logging.info(f"  {label} chars: {count:,} names")

        # Top countries if available
        if country_codes and with_country > 0:
            country_counts = Counter([r['country_code'] for r in final_data if r['country_code']])
            top_countries = country_counts.most_common(10)

            logging.info("\nTop 10 countries:")
            for country, count in top_countries:
                logging.info(f"  {country}: {count:,} authors")

        return final_data

    finally:
        conn.close()
        logging.info("Database connection closed")


# ==============================================================================
# OUTPUT FUNCTIONS
# ==============================================================================

def save_json(data: List[Dict], file_path: str):
    """Save data to JSON with pretty formatting"""
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    file_size = os.path.getsize(file_path)
    logging.info(f"Saved JSON: {file_path} ({file_size / 1024:.2f} KB)")


# ==============================================================================
# MAIN EXECUTION
# ==============================================================================

def main():
    """Main execution function"""
    setup_logging()

    logging.info("Starting name extraction...")
    logging.info(f"Configuration:")
    logging.info(f"  Database: {Config.DB_CONFIG['database']}@{Config.DB_CONFIG['host']}")
    logging.info(f"  Use name variants: {Config.USE_NAME_VARIANTS}")
    logging.info(f"  Use country context: {Config.USE_COUNTRY_CONTEXT}")
    logging.info(f"  Batch size: {Config.BATCH_SIZE:,}")
    logging.info(f"  Min forename length: {Config.MIN_FORENAME_LENGTH}")
    logging.info(f"  Output file: {Config.OUTPUT_FILE}")

    try:
        # Extract names
        result = extract_author_names()

        # Save output
        save_json(result, Config.OUTPUT_FILE)

        logging.info(f"\nOutput saved to: {Config.OUTPUT_FILE}")
        logging.info("=== STEP 1 COMPLETE ===\n")

        return 0

    except Exception as e:
        logging.error(f"Extraction failed: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())

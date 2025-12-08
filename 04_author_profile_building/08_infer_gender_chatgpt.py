#!/usr/bin/env python3
"""
Infer gender for unmatched names using ChatGPT API.

This script:
1. Reads author data from DuckDB database
2. Filters authors where gender inference is uncertain or missing
3. Uses ChatGPT API (gpt-5-nano) in batches to infer gender
4. Uses display_name for more accurate cultural/linguistic inference
5. Updates database with gpt_gender and gpt_probability columns

Requires OpenAI API key set as environment variable: OPENAI_API_KEY
"""

import sys
from pathlib import Path
import logging
from datetime import datetime
import argparse
import json
import os
import time
import duckdb

from openai import OpenAI

# Add current directory and parent directory to path for imports
SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(PARENT_DIR))

from config import OPENAI_API_KEY


def setup_logging():
    """
    Setup logging to both console and file with proper formatting.

    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logs directory if it doesn't exist
    log_dir = SCRIPT_DIR / 'logs'
    log_dir.mkdir(exist_ok=True)

    # Create log file with timestamp
    log_file = log_dir / f'{Path(__file__).stem}_{datetime.now():%Y%m%d_%H%M%S}.log'

    # Configure logging to both file and console
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
    Check if gpt_gender and gpt_probability columns exist and add them if not.

    Args:
        conn: DuckDB connection object

    Returns:
        None
    """
    logger = logging.getLogger(__name__)

    # Get current columns
    result = conn.execute("PRAGMA table_info(authors)").fetchall()
    existing_columns = {row[1] for row in result}  # row[1] is the column name

    logger.info(f"Existing columns: {existing_columns}")

    # Add gpt_gender column if it doesn't exist
    if 'gpt_gender' not in existing_columns:
        logger.info("Adding column: gpt_gender (TEXT)")
        conn.execute("ALTER TABLE authors ADD COLUMN gpt_gender TEXT")
    else:
        logger.info("Column already exists: gpt_gender")

    # Add gpt_probability column if it doesn't exist
    if 'gpt_probability' not in existing_columns:
        logger.info("Adding column: gpt_probability (DOUBLE)")
        conn.execute("ALTER TABLE authors ADD COLUMN gpt_probability DOUBLE")
    else:
        logger.info("Column already exists: gpt_probability")


def infer_gender_batch(client, people, logger):
    """
    Infer gender for a batch of people using ChatGPT API (gpt-5-nano).

    Args:
        client: OpenAI client instance
        people: List of dicts with 'display_name', 'country_name', 'author_id'
        logger: Logger instance

    Returns:
        tuple: (list of dicts with gender predictions, total_tokens)
    """
    # Build input lines with full display names and country context
    lines = [f"{i+1}. {p['display_name']} | Country: {p.get('country_name', 'unknown')}"
             for i, p in enumerate(people)]
    payload = "\n".join(lines)

    prompt = (
        "You are a linguistic name etymology analyzer. Based on historical naming patterns across cultures, "
        "analyze the statistical gender association of these names from a scientific publication database.\n\n"
        "For each name, determine the predominant gender association based on:\n"
        "- Name etymology and linguistic roots\n"
        "- Cultural naming traditions in the specified country\n"
        "- Historical usage patterns in academic literature\n\n"
        "Names:\n" + payload + "\n\n"
        "Return a JSON array with this structure:\n"
        '[{"name": "Full Name", "gender": "male", "probability": 0.95}, ...]\n\n'
        'Where gender is "male", "female", or "unknown" and probability is 0-1.\n\n'
        "Respond with ONLY the JSON array:"
    )

    try:
        response = client.chat.completions.create(
            model="gpt-5-nano",
            messages=[{"role": "user", "content": prompt}],
            reasoning_effort="minimal",  # Minimize reasoning tokens to get direct output
            max_completion_tokens=10000  # Increased for batch_size=250
        )

        if not response.choices or len(response.choices) == 0:
            logger.error("No choices in response")
            return None, 0

        text = response.choices[0].message.content

        # Log token usage
        usage = response.usage
        logger.info(f"API Response - prompt_tokens: {usage.prompt_tokens}, completion_tokens: {usage.completion_tokens}, total: {usage.total_tokens}")

        # Check for reasoning tokens (if present)
        if hasattr(usage, 'completion_tokens_details'):
            logger.info(f"Completion tokens details: {usage.completion_tokens_details}")

        # Log finish reason
        finish_reason = response.choices[0].finish_reason
        logger.info(f"Finish reason: {finish_reason}")

        # Log content preview
        logger.info(f"Content preview: {repr(text[:200] if text else '(empty)')}")

        # Parse JSON response
        if not text or not text.strip():
            logger.error("Empty response from API - all tokens may have been used for reasoning")
            return None, 0

        # Strip markdown code fences if present (```json ... ```)
        text = text.strip()
        if text.startswith('```'):
            # Remove opening code fence
            lines_list = text.split('\n')
            if lines_list[0].startswith('```'):
                lines_list = lines_list[1:]
            # Remove closing code fence
            if lines_list and lines_list[-1].strip() == '```':
                lines_list = lines_list[:-1]
            text = '\n'.join(lines_list)

        results = json.loads(text)

        # Ensure results is a list
        if not isinstance(results, list):
            logger.error(f"Expected JSON array, got: {type(results)}")
            return None, 0

        return results, usage.total_tokens

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse JSON response: {e}")
        logger.error(f"Response text: {text if 'text' in locals() else '(no response)'}")
        return None, 0
    except Exception as e:
        logger.error(f"API call failed: {e}")
        return None, 0


def match_results_to_people(people, results, logger):
    """
    Match ChatGPT results back to the original people list.

    Args:
        people: Original list of people dicts
        results: ChatGPT results list
        logger: Logger instance

    Returns:
        list: People list with gpt_gender and gpt_probability added
    """
    matched = []

    for i, person in enumerate(people):
        if results and i < len(results):
            result = results[i]
            person['gpt_gender'] = result.get('gender', 'unknown')
            person['gpt_probability'] = result.get('probability', 0.0)
        else:
            person['gpt_gender'] = 'unknown'
            person['gpt_probability'] = 0.0
            logger.warning(f"No result for: {person['display_name']}")

        matched.append(person)

    return matched


def infer_gender_in_duckdb(db_file, api_key=None, batch_size=250, limit=None):
    """
    Infer gender for authors in DuckDB database using ChatGPT API (gpt-5-nano).

    This function:
    1. Connects to the DuckDB database
    2. Ensures gpt_gender and gpt_probability columns exist
    3. Reads authors without gender info in batches
    4. Uses ChatGPT gpt-5-nano to infer gender based on display_name and country
    5. Updates the database with inferred gender and probability
    6. Tracks API usage statistics

    Args:
        db_file (str or Path): Path to the DuckDB database file
        api_key (str, optional): OpenAI API key
        batch_size (int): Number of names per API batch
        limit (int, optional): Limit number of authors to process (for testing)

    Returns:
        tuple: (total_records, stats_dict)
    """
    logger = logging.getLogger(__name__)

    db_file = Path(db_file)

    # Validate database file exists
    if not db_file.exists():
        raise FileNotFoundError(f"Database file not found: {db_file}")

    logger.info(f"Database file: {db_file}")

    # Get API key
    if not api_key:
        api_key = OPENAI_API_KEY

    if not api_key or api_key == 'your-api-key-here':
        raise ValueError("OpenAI API key not configured. Please add your API key to config.py or use --api-key argument.")

    # Initialize OpenAI client
    logger.info("Initializing OpenAI client...")
    client = OpenAI(api_key=api_key)
    logger.info("OpenAI client initialized successfully")

    # Connect to DuckDB
    conn = duckdb.connect(str(db_file))
    logger.info("DuckDB connection established")

    # Ensure columns exist
    logger.info("Checking for gpt_gender and gpt_probability columns...")
    ensure_columns_exist(conn)

    # Get count of authors to process (those without confident gender predictions)
    # Process authors where:
    # - All gender inference columns are NULL/empty OR
    # - Gender is 'no_forename' OR
    # - We don't have GPT results yet
    count_query = """
        SELECT COUNT(*) FROM authors
        WHERE (gender IS NULL OR gender = 'no_forename' OR gender = '')
        AND (gpt_gender IS NULL OR gpt_gender = '')
    """
    total_count = conn.execute(count_query).fetchone()[0]
    logger.info(f"Total authors to process: {total_count:,}")

    # Apply limit if specified
    if limit and limit < total_count:
        logger.info(f"Limiting to first {limit} authors (out of {total_count} total)")
        total_count = limit

    if total_count == 0:
        logger.info("No authors need GPT inference. Exiting.")
        conn.close()
        return 0, {}

    # Statistics
    total_processed = 0
    total_tokens = 0
    male_count = 0
    female_count = 0
    unknown_count = 0
    high_confidence_count = 0  # >= 0.8
    medium_confidence_count = 0  # 0.5-0.8
    low_confidence_count = 0  # < 0.5
    start_time = datetime.now()

    logger.info("Starting gender inference with ChatGPT...")

    # Process batches
    offset = 0
    while offset < total_count:
        # Fetch batch
        fetch_query = """
            SELECT author_id, display_name, country_name
            FROM authors
            WHERE (gender IS NULL OR gender = 'no_forename' OR gender = '')
            AND (gpt_gender IS NULL OR gpt_gender = '')
            LIMIT ? OFFSET ?
        """
        batch = conn.execute(fetch_query, [batch_size, offset]).fetchall()

        if not batch:
            break

        # Prepare people list for API
        people = []
        for author_id, display_name, country_name in batch:
            people.append({
                'author_id': author_id,
                'display_name': display_name if display_name else '',
                'country_name': country_name if country_name else ''
            })

        batch_num = (offset // batch_size) + 1
        total_batches = (total_count + batch_size - 1) // batch_size

        logger.info(f"Processing batch {batch_num}/{total_batches} ({len(people)} names)...")

        # Call ChatGPT API (gpt-5-nano)
        results, tokens = infer_gender_batch(client, people, logger)
        total_tokens += tokens

        if results:
            matched = match_results_to_people(people, results, logger)

            # Prepare updates
            updates = []
            for person in matched:
                gender = person['gpt_gender']
                probability = person['gpt_probability']

                # Update statistics
                if gender == 'male':
                    male_count += 1
                elif gender == 'female':
                    female_count += 1
                else:
                    unknown_count += 1

                if probability >= 0.8:
                    high_confidence_count += 1
                elif probability >= 0.5:
                    medium_confidence_count += 1
                else:
                    low_confidence_count += 1

                updates.append((gender, probability, person['author_id']))

            # Perform batch update
            conn.executemany(
                """
                UPDATE authors
                SET gpt_gender = ?, gpt_probability = ?
                WHERE author_id = ?
                """,
                updates
            )

            total_processed += len(matched)
        else:
            logger.error(f"Batch {batch_num} failed - skipping")
            total_processed += len(people)
            unknown_count += len(people)
            low_confidence_count += len(people)

        offset += batch_size

        # Rate limiting: small delay between batches
        if offset < total_count:
            time.sleep(0.5)

        # Log progress
        elapsed = (datetime.now() - start_time).total_seconds()
        rate = total_processed / elapsed if elapsed > 0 else 0
        pct_complete = (total_processed / total_count * 100) if total_count > 0 else 0

        logger.info(
            f"Progress: {total_processed:,}/{total_count:,} ({pct_complete:.1f}%) | "
            f"Rate: {rate:.1f} names/sec | "
            f"Tokens: {total_tokens:,}"
        )

    # Close connection
    conn.close()
    logger.info("DuckDB connection closed")

    # Final statistics
    total_elapsed = (datetime.now() - start_time).total_seconds()
    avg_rate = total_processed / total_elapsed if total_elapsed > 0 else 0
    success_rate = ((male_count + female_count) / total_processed * 100) if total_processed > 0 else 0

    # Estimate cost for gpt-5-nano
    # gpt-5-nano pricing: $0.05 per 1M input, $0.40 per 1M output
    # Estimate 60/40 split between input and output tokens
    estimated_cost = (total_tokens * 0.6 / 1_000_000 * 0.05) + (total_tokens * 0.4 / 1_000_000 * 0.40)

    logger.info("="*70)
    logger.info("CHATGPT GENDER INFERENCE COMPLETE")
    logger.info("="*70)
    logger.info(f"Total records processed: {total_processed:,}")
    logger.info("")
    logger.info("Gender Distribution:")
    logger.info(f"  Male: {male_count:,} ({male_count/total_processed*100:.2f}%)" if total_processed > 0 else "  Male: 0")
    logger.info(f"  Female: {female_count:,} ({female_count/total_processed*100:.2f}%)" if total_processed > 0 else "  Female: 0")
    logger.info(f"  Unknown: {unknown_count:,} ({unknown_count/total_processed*100:.2f}%)" if total_processed > 0 else "  Unknown: 0")
    logger.info(f"  Success rate (M/F): {success_rate:.2f}%")
    logger.info("")
    logger.info("Confidence Distribution:")
    logger.info(f"  High (>=0.8): {high_confidence_count:,} ({high_confidence_count/total_processed*100:.2f}%)" if total_processed > 0 else "  High: 0")
    logger.info(f"  Medium (0.5-0.8): {medium_confidence_count:,} ({medium_confidence_count/total_processed*100:.2f}%)" if total_processed > 0 else "  Medium: 0")
    logger.info(f"  Low (<0.5): {low_confidence_count:,} ({low_confidence_count/total_processed*100:.2f}%)" if total_processed > 0 else "  Low: 0")
    logger.info("")
    logger.info(f"Total API tokens used: {total_tokens:,}")
    logger.info(f"Estimated cost: ${estimated_cost:.4f}")
    logger.info(f"Total time: {total_elapsed:.2f} seconds")
    logger.info(f"Average rate: {avg_rate:.1f} names/sec")
    logger.info("="*70)

    stats = {
        'male': male_count,
        'female': female_count,
        'unknown': unknown_count,
        'high_confidence': high_confidence_count,
        'medium_confidence': medium_confidence_count,
        'low_confidence': low_confidence_count,
        'total_tokens': total_tokens,
        'estimated_cost': estimated_cost
    }

    return total_processed, stats


def main():
    """
    Main entry point for the script.

    Parses command line arguments and initiates the ChatGPT gender inference.
    """
    # Default database path
    default_db_path = SCRIPT_DIR / 'datasets' / 'author_data.duckdb'

    parser = argparse.ArgumentParser(
        description='Infer gender for authors using ChatGPT gpt-5-nano API.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Infer gender from default database
  python 08_infer_gender_chatgpt.py

  # Test with limited records
  python 08_infer_gender_chatgpt.py --limit 100

  # Custom batch size and database
  python 08_infer_gender_chatgpt.py --db datasets/custom.duckdb --batch-size 50

API Requirements:
  - OpenAI API key required (set in config.py or --api-key)
  - Uses gpt-5-nano model (fastest and cheapest GPT-5 model)

Model Pricing:
  - gpt-5-nano: $0.05 per 1M input tokens, $0.40 per 1M output tokens
  - Estimated cost: ~$0.007 per 1000 names (with batch_size=250, reasoning_effort='minimal')

Output:
  - gpt_gender: male, female, or unknown
  - gpt_probability: confidence score (0-1)
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
        default=250,
        help='Number of names to process per API call (default: 250, optimized for cost efficiency)'
    )

    parser.add_argument(
        '--api-key',
        type=str,
        default=None,
        help='OpenAI API key (or set in config.py)'
    )

    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limit number of authors to process (useful for testing, e.g., --limit 100)'
    )

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging()

    logger.info("="*70)
    logger.info("CHATGPT GENDER INFERENCE (GPT-5-NANO)")
    logger.info("="*70)
    logger.info(f"Database file: {args.db}")
    logger.info("Model: gpt-5-nano")
    logger.info(f"Batch size: {args.batch_size}")
    if args.limit:
        logger.info(f"Processing limit: {args.limit} authors")
    logger.info("="*70)

    try:
        # Run ChatGPT gender inference
        total_records, stats = infer_gender_in_duckdb(
            db_file=args.db,
            api_key=args.api_key,
            batch_size=args.batch_size,
            limit=args.limit
        )

        logger.info("Script completed successfully")
        return 0

    except FileNotFoundError as e:
        logger.error(f"File error: {e}")
        return 1
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return 1
    except Exception as e:
        logger.critical(f"Script failed with error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())

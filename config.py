#!/usr/bin/env python3
"""
Global configuration for OpenAlex database parsing
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
# This loads variables from .env into the environment
# Priority: 1) Already set env vars, 2) .env file, 3) defaults in code
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

# Database configuration
# Can be overridden with environment variables when running in Docker on NAS
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '192.168.1.162'),  # New NAS IP (or 'postgres' when in container)
    'port': int(os.getenv('DB_PORT', '55432')),     # External port (5432 when in container)
    'database': os.getenv('DB_NAME', 'oadbv5'),
    'user': os.getenv('DB_USER', 'admin'),
    'password': os.getenv('ADMIN_PASSWORD', 'secure_password_123')
}

# File paths
# Support both local Mac development and Docker container paths
PARSING_DIR = os.getenv('PARSING_DIR', '/Users/lucas/Documents/openalex_database/python/OA_clone/03_snapshot_parsing')
SNAPSHOT_DIR = os.getenv('SNAPSHOT_DIR', '/Volumes/Series/25NOV2025/data')  # Updated snapshot location

# Entity directories - will process ALL updated_date=* subdirectories
GZ_DIRECTORIES = {
    'topics': f'{SNAPSHOT_DIR}/topics',
    'concepts': f'{SNAPSHOT_DIR}/concepts',
    'publishers': f'{SNAPSHOT_DIR}/publishers',
    'funders': f'{SNAPSHOT_DIR}/funders',
    'sources': f'{SNAPSHOT_DIR}/sources',
    'institutions': f'{SNAPSHOT_DIR}/institutions',
    'authors': f'{SNAPSHOT_DIR}/authors',
    'works': f'{SNAPSHOT_DIR}/works',
}

# Legacy single file paths (for backwards compatibility)
GZ_FILES = {
    'topics': f'{PARSING_DIR}/topics_data.gz',
    'concepts': f'{PARSING_DIR}/concepts_data.gz',
    'publishers': f'{PARSING_DIR}/publishers_data.gz',
    'funders': f'{PARSING_DIR}/funders_data.gz',
    'sources': f'{PARSING_DIR}/sources_data.gz',
    'institutions': f'{PARSING_DIR}/institutions_data.gz',
    'authors': f'{PARSING_DIR}/author_data.gz',
    'works': f'{PARSING_DIR}/works_data.gz',
}

# Parsing configuration
BATCH_SIZE = 50000  # Records to accumulate before COPY
PROGRESS_INTERVAL = 10000  # Print progress every N lines
LINE_LIMIT = None  # Set to integer for testing (e.g., 100000)

# Logging configuration
# Support both local Mac development and Docker container paths
LOG_DIR = os.getenv('LOG_DIR', '/Users/lucas/Documents/openalex_database/python/OA_clone/03_snapshot_parsing/logs')
os.makedirs(LOG_DIR, exist_ok=True)

# Performance settings
USE_UNLOGGED_TABLES = False  # Set True to disable WAL (faster, but no crash recovery)
PARALLEL_PARSERS = 4  # Number of parsers to run in parallel for Phase 1

# OpenAI API configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
# Note: OPENAI_API_KEY is only required for scripts that use ChatGPT inference
# Other scripts can run without it
if not OPENAI_API_KEY:
    import warnings
    warnings.warn(
        "OPENAI_API_KEY not set. ChatGPT-based gender inference will not work. "
        "Set OPENAI_API_KEY in your .env file if you need this functionality.",
        UserWarning
    )

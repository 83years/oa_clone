#!/usr/bin/env python3
"""
Global configuration for OpenAlex database parsing
"""
import os

# Database configuration
DB_CONFIG = {
    'host': '192.168.1.100',
    'port': 55432,
    'database': 'oadb2',
    'user': 'admin',
    'password': os.getenv('ADMIN_PASSWORD', 'secure_password_123')
}

# File paths
PARSING_DIR = '/Users/lucas/Documents/openalex_database/python/OA_clone/03_snapshot_parsing'
SNAPSHOT_DIR = '/Volumes/OA_snapshot/24OCT2025/data'

# Updated snapshot directories (latest dates as of Nov 2025)
GZ_DIRECTORIES = {
    'topics': f'{SNAPSHOT_DIR}/topics/updated_date=2025-09-29',
    'concepts': f'{SNAPSHOT_DIR}/concepts/updated_date=2025-10-01',
    'publishers': f'{SNAPSHOT_DIR}/publishers/updated_date=2025-10-01',
    'funders': f'{SNAPSHOT_DIR}/funders/updated_date=2025-10-01',
    'sources': f'{SNAPSHOT_DIR}/sources/updated_date=2025-10-01',
    'institutions': f'{SNAPSHOT_DIR}/institutions/updated_date=2025-10-01',
    'authors': f'{SNAPSHOT_DIR}/authors/updated_date=2025-09-30',
    'works': f'{SNAPSHOT_DIR}/works/updated_date=2025-09-30',
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
LOG_DIR = '/Users/lucas/Documents/openalex_database/python/OA_clone/03_snapshot_parsing/logs'
os.makedirs(LOG_DIR, exist_ok=True)

# Performance settings
USE_UNLOGGED_TABLES = False  # Set True to disable WAL (faster, but no crash recovery)
PARALLEL_PARSERS = 4  # Number of parsers to run in parallel for Phase 1

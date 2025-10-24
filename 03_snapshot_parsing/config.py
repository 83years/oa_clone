"""
Configuration for OpenAlex snapshot parsing
"""
import os

# Database configuration - matches Docker setup
DB_CONFIG = {
    'host': os.getenv('DB_HOST', '192.168.1.100'),
    'port': int(os.getenv('DB_PORT', '55432')),
    'database': os.getenv('DB_NAME', 'OADB'),
    'user': os.getenv('DB_USER', 'admin'),
    'password': os.getenv('DB_PASSWORD', 'secure_password_123')
}

# OpenAlex snapshot data location
DATA_ROOT = '/Volumes/OA_snapshot/03OCT2025/openalex-snapshot/data'

# Processing configuration
BATCH_SIZE = 100000  # Records per batch for COPY operations
PROGRESS_INTERVAL = 10000  # Report progress every N records

# Entity processing order (respects foreign key dependencies)
PROCESSING_ORDER = [
    'topics',
    'concepts',
    'publishers',
    'funders',
    'sources',
    'institutions',
    'authors'
]

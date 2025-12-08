#!/usr/bin/env python3
"""
OpenAlex Merged IDs Downloader

Downloads merged ID files from the OpenAlex S3 bucket.
These files contain mappings between old and new entity IDs across different versions.

Bucket: openalex
Prefix: merged_ids/
"""

import os
import boto3
import logging
from datetime import datetime
from pathlib import Path
from botocore import UNSIGNED
from botocore.config import Config
from botocore.exceptions import ClientError
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Configuration
BUCKET_NAME = "openalex"
PREFIX = "legacy-data/merged_ids/"  # Only download files in this prefix
LOCAL_BASE_PATH = "/Volumes/Series/25NOV2025/merged_ids"
MAX_WORKERS = 8  # Parallel downloads
RETRY_ATTEMPTS = 3  # Retry failed downloads

# Create logs directory
log_dir = Path(__file__).parent / 'logs'
log_dir.mkdir(exist_ok=True)

# Setup logging to both file and console
log_file = log_dir / f'{Path(__file__).stem}_{datetime.now():%Y%m%d_%H%M%S}.log'

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()  # Console output
    ]
)

logger = logging.getLogger(__name__)


class MergedIDsDownloader:
    """Download merged ID files from OpenAlex S3 bucket"""

    def __init__(self):
        logger.info(f"Initializing MergedIDsDownloader")
        logger.info(f"Log file: {log_file}")

        # Create S3 client for public bucket (no credentials needed)
        self.s3_client = boto3.client(
            's3',
            config=Config(signature_version=UNSIGNED, max_pool_connections=50)
        )

        # Create local directory
        Path(LOCAL_BASE_PATH).mkdir(parents=True, exist_ok=True)
        logger.info(f"Local destination: {LOCAL_BASE_PATH}")

        # Statistics
        self.downloaded_files = 0
        self.skipped_files = 0
        self.failed_files = 0
        self.total_bytes = 0
        self.start_time = time.time()
        self.lock = threading.Lock()

    def get_file_info(self, key):
        """Get metadata about a file in S3"""
        try:
            response = self.s3_client.head_object(Bucket=BUCKET_NAME, Key=key)
            return {
                'size': response.get('ContentLength', 0),
                'last_modified': response.get('LastModified')
            }
        except ClientError as e:
            logger.error(f"Failed to get file info for {key}: {e}")
            return None

    def should_download_file(self, key, s3_info):
        """Check if file should be downloaded (not exists or different size)"""
        # Remove prefix to get relative path
        relative_path = key.replace(PREFIX, '', 1)
        local_path = os.path.join(LOCAL_BASE_PATH, relative_path)

        if not os.path.exists(local_path):
            return True, local_path

        local_size = os.path.getsize(local_path)
        s3_size = s3_info['size']

        if local_size != s3_size:
            logger.warning(f"Size mismatch for {key}: local={local_size}, s3={s3_size}")
            return True, local_path

        return False, local_path

    def download_file(self, key, attempt=1):
        """Download a single file from S3 with retry logic"""
        try:
            # Get file info
            s3_info = self.get_file_info(key)
            if not s3_info:
                with self.lock:
                    self.failed_files += 1
                return False

            # Check if we need to download
            should_download, local_path = self.should_download_file(key, s3_info)

            if not should_download:
                with self.lock:
                    self.skipped_files += 1
                logger.debug(f"Skipping {key} - already exists with correct size")
                return True

            # Create local directory if it doesn't exist
            local_dir = os.path.dirname(local_path)
            Path(local_dir).mkdir(parents=True, exist_ok=True)

            # Download the file
            s3_size = s3_info['size']
            logger.info(f"Downloading {key} ({s3_size / (1024*1024):.2f} MB) [Attempt {attempt}/{RETRY_ATTEMPTS}]")

            # Download to temporary file first
            temp_path = local_path + '.tmp'

            with open(temp_path, 'wb') as f:
                self.s3_client.download_fileobj(
                    Bucket=BUCKET_NAME,
                    Key=key,
                    Fileobj=f,
                    Config=boto3.s3.transfer.TransferConfig(
                        multipart_threshold=1024 * 25,  # 25MB
                        max_concurrency=10,
                        multipart_chunksize=1024 * 25,
                        use_threads=True
                    )
                )

            # Verify file size
            downloaded_size = os.path.getsize(temp_path)
            if downloaded_size != s3_size:
                logger.error(f"Size mismatch for {key}: expected={s3_size}, got={downloaded_size}")
                os.remove(temp_path)

                # Retry if attempts remain
                if attempt < RETRY_ATTEMPTS:
                    logger.info(f"Retrying download of {key}")
                    return self.download_file(key, attempt + 1)
                else:
                    with self.lock:
                        self.failed_files += 1
                    return False

            # Move temp file to final location
            if os.path.exists(local_path):
                os.remove(local_path)
            os.rename(temp_path, local_path)

            with self.lock:
                self.downloaded_files += 1
                self.total_bytes += s3_size

            logger.info(f"Successfully downloaded {key}")
            return True

        except Exception as e:
            logger.error(f"Failed to download {key}: {str(e)}")

            # Retry if attempts remain
            if attempt < RETRY_ATTEMPTS:
                logger.info(f"Retrying download of {key}")
                time.sleep(2 ** attempt)  # Exponential backoff
                return self.download_file(key, attempt + 1)

            with self.lock:
                self.failed_files += 1

            # Remove temporary or partial file if it exists
            temp_path = local_path + '.tmp' if 'local_path' in locals() else None
            for path in [temp_path, locals().get('local_path')]:
                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except:
                        pass

            return False

    def list_merged_id_files(self):
        """List all merged ID files in the S3 bucket"""
        logger.info(f"Listing objects in s3://{BUCKET_NAME}/{PREFIX}...")
        objects = []
        paginator = self.s3_client.get_paginator('list_objects_v2')

        try:
            page_count = 0
            for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=PREFIX):
                page_count += 1

                if 'Contents' in page:
                    for obj in page['Contents']:
                        # Skip directory markers
                        if not obj['Key'].endswith('/'):
                            objects.append(obj['Key'])

                    if len(objects) % 100 == 0:
                        logger.info(f"Found {len(objects)} files so far...")

                logger.debug(f"Processed page {page_count}")

        except ClientError as e:
            logger.error(f"Error listing objects: {e}")
            return []

        logger.info(f"Found {len(objects)} merged ID files to process")
        return objects

    def print_statistics(self):
        """Print download statistics"""
        elapsed = time.time() - self.start_time
        hours = elapsed // 3600
        minutes = (elapsed % 3600) // 60
        seconds = elapsed % 60

        total_files = self.downloaded_files + self.skipped_files + self.failed_files

        logger.info("=" * 70)
        logger.info("DOWNLOAD STATISTICS")
        logger.info("=" * 70)
        logger.info(f"Total files processed:  {total_files:,}")
        logger.info(f"Files downloaded:       {self.downloaded_files:,}")
        logger.info(f"Files skipped:          {self.skipped_files:,}")
        logger.info(f"Files failed:           {self.failed_files:,}")
        logger.info(f"Total data downloaded:  {self.total_bytes / (1024**3):.2f} GB")
        logger.info(f"Time elapsed:           {int(hours)}h {int(minutes)}m {int(seconds)}s")

        if elapsed > 0:
            rate = self.total_bytes / elapsed / (1024**2)
            logger.info(f"Average download rate:  {rate:.2f} MB/s")

        if total_files > 0:
            success_rate = ((self.downloaded_files + self.skipped_files) / total_files) * 100
            logger.info(f"Success rate:           {success_rate:.1f}%")

        logger.info("=" * 70)

    def download_all(self):
        """Download all merged ID files"""
        logger.info("Starting merged IDs download...")
        logger.info(f"Source: s3://{BUCKET_NAME}/{PREFIX}")
        logger.info(f"Destination: {LOCAL_BASE_PATH}")

        # Get list of all merged ID files
        all_files = self.list_merged_id_files()

        if not all_files:
            logger.warning("No files found or error listing bucket")
            return

        logger.info(f"Starting download of {len(all_files)} files using {MAX_WORKERS} workers...")

        # Download files using thread pool
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Submit all download tasks
            future_to_key = {
                executor.submit(self.download_file, key): key
                for key in all_files
            }

            # Process completed downloads
            completed = 0
            for future in as_completed(future_to_key):
                completed += 1
                key = future_to_key[future]

                # Print progress periodically
                if completed % 10 == 0 or completed == len(all_files):
                    progress = (completed / len(all_files)) * 100
                    logger.info(f"Progress: {completed}/{len(all_files)} ({progress:.1f}%)")

                # Print statistics every 50 files
                if completed % 50 == 0:
                    self.print_statistics()

        logger.info("Download completed!")
        self.print_statistics()

        # Log failed files if any
        if self.failed_files > 0:
            logger.warning(f"{self.failed_files} files failed to download. Check logs for details.")


def main():
    """Main function"""
    print("=" * 70)
    print("OpenAlex Merged IDs Downloader")
    print("=" * 70)
    print(f"This will download merged ID files from OpenAlex S3 bucket")
    print(f"Destination: {LOCAL_BASE_PATH}")
    print(f"Log file: {log_file}")
    print()

    # Create downloader and start
    downloader = MergedIDsDownloader()

    try:
        downloader.download_all()
    except KeyboardInterrupt:
        logger.info("Download interrupted by user")
        downloader.print_statistics()
    except Exception as e:
        logger.error(f"Download failed with error: {e}", exc_info=True)
        downloader.print_statistics()


if __name__ == "__main__":
    main()

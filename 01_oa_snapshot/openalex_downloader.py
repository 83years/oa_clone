#!/usr/bin/env python3
"""
OpenAlex Repository Downloader
Downloads the entire OpenAlex dataset from S3 to local storage.
WARNING: This will download several terabytes of data!
"""

import os
import boto3
import logging
from datetime import datetime
from pathlib import Path
from botocore import UNSIGNED
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Configuration
BUCKET_NAME = "openalex"
LOCAL_BASE_PATH = "/Volumes/OA_snapshot/24OCT2025"
MAX_WORKERS = 10  # Adjust based on your bandwidth and system
CHUNK_SIZE = 8 * 1024 * 1024  # 8MB chunks

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('openalex_download.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class OpenAlexDownloader:
    def __init__(self):
        # Create S3 client for public bucket (no credentials needed)
        self.s3_client = boto3.client(
            's3',
            config=Config(signature_version=UNSIGNED, max_pool_connections=50)
        )
        
        # Create local directory
        Path(LOCAL_BASE_PATH).mkdir(parents=True, exist_ok=True)
        
        # Statistics
        self.downloaded_files = 0
        self.skipped_files = 0
        self.failed_files = 0
        self.total_bytes = 0
        self.start_time = time.time()
        self.lock = threading.Lock()
    
    def get_file_size(self, key):
        """Get the size of a file in S3"""
        try:
            response = self.s3_client.head_object(Bucket=BUCKET_NAME, Key=key)
            return response.get('ContentLength', 0)
        except ClientError:
            return 0
    
    def should_download_file(self, key, s3_size):
        """Check if file should be downloaded (not exists or different size)"""
        local_path = os.path.join(LOCAL_BASE_PATH, key)
        
        if not os.path.exists(local_path):
            return True
        
        local_size = os.path.getsize(local_path)
        return local_size != s3_size
    
    def download_file(self, key):
        """Download a single file from S3"""
        local_path = os.path.join(LOCAL_BASE_PATH, key)
        local_dir = os.path.dirname(local_path)
        
        try:
            # Create local directory if it doesn't exist
            Path(local_dir).mkdir(parents=True, exist_ok=True)
            
            # Get file size
            s3_size = self.get_file_size(key)
            
            # Check if we need to download
            if not self.should_download_file(key, s3_size):
                with self.lock:
                    self.skipped_files += 1
                logger.debug(f"Skipping {key} - already exists with correct size")
                return True
            
            # Download the file
            logger.info(f"Downloading {key} ({s3_size / (1024*1024):.1f} MB)")
            
            with open(local_path, 'wb') as f:
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
            if os.path.getsize(local_path) != s3_size:
                logger.warning(f"Size mismatch for {key}")
                return False
            
            with self.lock:
                self.downloaded_files += 1
                self.total_bytes += s3_size
            
            logger.info(f"Successfully downloaded {key}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to download {key}: {str(e)}")
            with self.lock:
                self.failed_files += 1
            
            # Remove partial file if it exists
            if os.path.exists(local_path):
                try:
                    os.remove(local_path)
                except:
                    pass
            
            return False
    
    def list_all_objects(self):
        """List all objects in the S3 bucket"""
        logger.info("Listing all objects in the OpenAlex bucket...")
        objects = []
        paginator = self.s3_client.get_paginator('list_objects_v2')
        
        try:
            for page in paginator.paginate(Bucket=BUCKET_NAME):
                if 'Contents' in page:
                    for obj in page['Contents']:
                        objects.append(obj['Key'])
                        if len(objects) % 1000 == 0:
                            logger.info(f"Found {len(objects)} objects so far...")
        
        except ClientError as e:
            logger.error(f"Error listing objects: {e}")
            return []
        
        logger.info(f"Found {len(objects)} total objects to process")
        return objects
    
    def print_statistics(self):
        """Print download statistics"""
        elapsed = time.time() - self.start_time
        hours = elapsed // 3600
        minutes = (elapsed % 3600) // 60
        
        total_files = self.downloaded_files + self.skipped_files + self.failed_files
        
        logger.info("="*60)
        logger.info("DOWNLOAD STATISTICS")
        logger.info("="*60)
        logger.info(f"Total files processed: {total_files}")
        logger.info(f"Files downloaded: {self.downloaded_files}")
        logger.info(f"Files skipped: {self.skipped_files}")
        logger.info(f"Files failed: {self.failed_files}")
        logger.info(f"Total data downloaded: {self.total_bytes / (1024**3):.2f} GB")
        logger.info(f"Time elapsed: {int(hours)}h {int(minutes)}m")
        
        if elapsed > 0:
            rate = self.total_bytes / elapsed / (1024**2)
            logger.info(f"Average download rate: {rate:.2f} MB/s")
        
        logger.info("="*60)
    
    def download_repository(self):
        """Download the entire OpenAlex repository"""
        logger.info("Starting OpenAlex repository download...")
        logger.info(f"Destination: {LOCAL_BASE_PATH}")
        logger.warning("WARNING: This will download several terabytes of data!")
        
        # Get list of all objects
        all_objects = self.list_all_objects()
        
        if not all_objects:
            logger.error("No objects found or error listing bucket")
            return
        
        logger.info(f"Starting download of {len(all_objects)} files using {MAX_WORKERS} workers...")
        
        # Download files using thread pool
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Submit all download tasks
            future_to_key = {
                executor.submit(self.download_file, key): key 
                for key in all_objects
            }
            
            # Process completed downloads
            for future in as_completed(future_to_key):
                key = future_to_key[future]
                
                # Print progress every 100 files
                total_processed = self.downloaded_files + self.skipped_files + self.failed_files
                if total_processed % 100 == 0:
                    progress = (total_processed / len(all_objects)) * 100
                    logger.info(f"Progress: {total_processed}/{len(all_objects)} ({progress:.1f}%)")
                    self.print_statistics()
        
        logger.info("Download completed!")
        self.print_statistics()

def main():
    """Main function"""
    print("OpenAlex Repository Downloader")
    print("="*50)
    print(f"This will download the entire OpenAlex dataset to: {LOCAL_BASE_PATH}")
    print("WARNING: This is several terabytes of data and may take days to complete!")
    print("Press Ctrl+C at any time to stop the download.")
    print()
    
    # Ask for confirmation
    response = input("Do you want to proceed? (yes/no): ").lower().strip()
    if response != 'yes':
        print("Download cancelled.")
        return
    
    # Create downloader and start
    downloader = OpenAlexDownloader()
    
    try:
        downloader.download_repository()
    except KeyboardInterrupt:
        logger.info("Download interrupted by user")
        downloader.print_statistics()
    except Exception as e:
        logger.error(f"Download failed: {e}")
        downloader.print_statistics()

if __name__ == "__main__":
    main()
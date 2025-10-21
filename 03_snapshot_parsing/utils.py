#!/usr/bin/env python3
"""
Shared utilities for OpenAlex ETL processing
"""
import json
import time
import psycopg2
import io
from datetime import datetime
from pathlib import Path
import logging
from typing import Dict, Any, Optional, Tuple
import hashlib

class PerformanceMonitor:
    """Monitor and log performance metrics"""
    
    def __init__(self, logger: logging.Logger, report_interval: int = 1000):
        self.logger = logger
        self.report_interval = report_interval
        self.start_time = time.time()
        self.last_report_time = self.start_time
        self.last_report_count = 0
        self.total_records = 0
        
    def update(self, records_processed: int, batch_num: int = None, force: bool = False):
        """Update metrics and log if interval reached"""
        self.total_records = records_processed
        
        if force or (records_processed - self.last_report_count) >= self.report_interval:
            current_time = time.time()
            elapsed = current_time - self.start_time
            interval_time = current_time - self.last_report_time
            interval_records = records_processed - self.last_report_count
            
            # Calculate rates
            overall_rate = records_processed / elapsed if elapsed > 0 else 0
            interval_rate = interval_records / interval_time if interval_time > 0 else 0
            
            # Estimate time remaining
            eta_str = "Unknown"
            if hasattr(self, 'estimated_total') and self.estimated_total > 0:
                remaining = self.estimated_total - records_processed
                if interval_rate > 0:
                    eta_seconds = remaining / interval_rate
                    eta_str = self.format_duration(eta_seconds)
            
            msg = (f"Progress: {records_processed:,} records | "
                   f"Rate: {interval_rate:.0f}/s (current), {overall_rate:.0f}/s (avg) | "
                   f"Time: {self.format_duration(elapsed)}")
            
            if batch_num is not None:
                msg += f" | Batch: {batch_num}"
            
            if eta_str != "Unknown":
                msg += f" | ETA: {eta_str}"
            
            self.logger.info(msg)
            
            self.last_report_time = current_time
            self.last_report_count = records_processed
    
    def set_estimated_total(self, total: int):
        """Set estimated total for ETA calculation"""
        self.estimated_total = total
    
    def format_duration(self, seconds: float) -> str:
        """Format duration in human-readable format"""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"
    
    def final_report(self):
        """Generate final performance report"""
        total_time = time.time() - self.start_time
        rate = self.total_records / total_time if total_time > 0 else 0
        
        self.logger.info("="*70)
        self.logger.info(f"Processing completed:")
        self.logger.info(f"  Total records: {self.total_records:,}")
        self.logger.info(f"  Total time: {self.format_duration(total_time)}")
        self.logger.info(f"  Average rate: {rate:.0f} records/second")
        self.logger.info("="*70)

class BatchWriter:
    """Efficient batch writer using COPY for PostgreSQL"""
    
    def __init__(self, conn, table_name: str, columns: list, logger: logging.Logger, mode: str = 'clean'):
        self.conn = conn
        self.table_name = table_name
        self.columns = columns
        self.logger = logger
        self.mode = mode
        self.buffer = []
        
    def add_record(self, record: dict):
        """Add record to buffer"""
        # Ensure all columns are present in correct order
        row = []
        for col in self.columns:
            value = record.get(col)
            # Handle None/NULL values
            if value is None:
                row.append('\\N')
            elif isinstance(value, bool):
                row.append('t' if value else 'f')
            elif isinstance(value, (list, dict)):
                row.append(json.dumps(value).replace('\t', ' ').replace('\n', ' '))
            else:
                # Escape special characters for COPY format
                str_val = str(value)
                str_val = str_val.replace('\\', '\\\\')
                str_val = str_val.replace('\t', '\\t')
                str_val = str_val.replace('\n', '\\n')
                str_val = str_val.replace('\r', '\\r')
                row.append(str_val)
        
        self.buffer.append('\t'.join(row))
    
    def write_batch(self):
        """Write buffered records using COPY"""
        if not self.buffer:
            return 0
        
        cursor = self.conn.cursor()
        try:
            if self.mode == 'clean':
                # Direct COPY - fastest, assumes empty tables
                data = '\n'.join(self.buffer)
                cursor.copy_expert(
                    f"COPY {self.table_name} ({','.join(self.columns)}) "
                    f"FROM STDIN WITH (FORMAT text, NULL '\\N')",
                    io.StringIO(data)
                )
                
            else:  # mode == 'update'
                # Use temp table + INSERT with ON CONFLICT for updates
                temp_table = f"temp_{self.table_name}_{int(time.time() * 1000)}"
                
                # Create temp table
                cursor.execute(f"""
                    CREATE TEMP TABLE {temp_table} 
                    (LIKE {self.table_name} INCLUDING DEFAULTS)
                    ON COMMIT DROP
                """)
                
                # COPY into temp table
                data = '\n'.join(self.buffer)
                cursor.copy_expert(
                    f"COPY {temp_table} ({','.join(self.columns)}) "
                    f"FROM STDIN WITH (FORMAT text, NULL '\\N')",
                    io.StringIO(data)
                )
                
                # Insert from temp table, skip conflicts
                cols = ','.join(self.columns)
                cursor.execute(f"""
                    INSERT INTO {self.table_name} ({cols})
                    SELECT {cols} FROM {temp_table}
                    ON CONFLICT DO NOTHING
                """)
            
            records_written = len(self.buffer)
            self.buffer.clear()
            return records_written
            
        except Exception as e:
            self.logger.error(f"Error writing batch to {self.table_name}: {e}")
            
            # Add this to see the full PostgreSQL error:
            if hasattr(e, 'pgerror'):
                self.logger.error(f"PostgreSQL error: {e.pgerror}")
            if hasattr(e, 'diag'):
                self.logger.error(f"Error details: {e.diag.message_primary}")
                if e.diag.message_detail:
                    self.logger.error(f"Detail: {e.diag.message_detail}")
            
            # Also log some sample data to help debug
            if self.buffer:
                self.logger.error(f"First record in buffer: {self.buffer[0][:200]}")
            
            raise
        finally:
            cursor.close()

def setup_logging(name: str, log_dir: str = "logs") -> Tuple[logging.Logger, str]:
    """Setup comprehensive logging"""
    Path(log_dir).mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = Path(log_dir) / f"{name}_{timestamp}.log"
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # Remove existing handlers to avoid duplicates
    logger.handlers.clear()
    
    # File handler - detailed
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    
    # Console handler - less detailed
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(asctime)s | %(levelname)-8s | %(message)s',
                                       datefmt='%H:%M:%S')
    console_handler.setFormatter(console_format)
    
    # Add handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger, str(log_file)

def get_file_info(file_path: str) -> Dict[str, Any]:
    """Get file information for monitoring"""
    import gzip
    import os
    
    file_size = os.path.getsize(file_path)
    
    # Try to count lines for estimation (sample first 1000 lines)
    line_count_estimate = None
    try:
        with gzip.open(file_path, 'rt', encoding='utf-8') as f:
            sample_lines = 0
            sample_bytes = 0
            for _ in range(1000):
                line = f.readline()
                if not line:
                    break
                sample_lines += 1
                sample_bytes += len(line.encode('utf-8'))
            
            if sample_lines > 0 and sample_bytes > 0:
                # Estimate total lines based on sample
                avg_line_size = sample_bytes / sample_lines
                # Account for gzip compression ratio (typically 5-10x)
                line_count_estimate = int(file_size * 7 / avg_line_size)
    except:
        pass
    
    return {
        'file_size': file_size,
        'file_size_mb': file_size / (1024 * 1024),
        'line_count_estimate': line_count_estimate
    }

def generate_job_id(file_path: str, entity_type: str) -> str:
    """Generate unique job ID"""
    file_hash = hashlib.md5(file_path.encode()).hexdigest()[:8]
    return f"{entity_type}_{Path(file_path).stem}_{file_hash}"
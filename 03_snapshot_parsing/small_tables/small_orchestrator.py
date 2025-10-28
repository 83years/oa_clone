#!/usr/bin/env python3
"""
Production-Ready OpenAlex Orchestrator
Features: Resume capability, state tracking, detailed logging, entity selection
"""
import os
import sys
import subprocess
import json
import argparse
from pathlib import Path
from datetime import datetime
import psycopg2
from typing import Dict, List, Set

# Get script directory for absolute paths
SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent

# Add parent directory to path for config imports
sys.path.insert(0, str(PARENT_DIR))
from config import DB_CONFIG, DATA_ROOT, PROCESSING_ORDER

# Parser file mapping (authors moved to big_tables pipeline)
# Use absolute paths so parsers can be found regardless of working directory
PARSERS = {
    'topics': str(SCRIPT_DIR / 'parse_topics.py'),
    'concepts': str(SCRIPT_DIR / 'parse_concepts.py'),
    'publishers': str(SCRIPT_DIR / 'parse_publishers.py'),
    'funders': str(SCRIPT_DIR / 'parse_funders.py'),
    'sources': str(SCRIPT_DIR / 'parse_sources.py'),
    'institutions': str(SCRIPT_DIR / 'parse_institutions.py')
}

# State file in same directory as orchestrator
STATE_FILE = str(SCRIPT_DIR / 'orchestrator_state.json')

class ProcessingState:
    """Track which files have been processed"""
    
    def __init__(self, state_file: str = STATE_FILE):
        self.state_file = state_file
        self.completed_files: Set[str] = set()
        self.failed_files: Dict[str, str] = {}
        self.started_at: str = None
        self.last_updated: str = None
        self.load_state()
    
    def load_state(self):
        """Load existing state from file"""
        if Path(self.state_file).exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self.completed_files = set(data.get('completed_files', []))
                    self.failed_files = data.get('failed_files', {})
                    self.started_at = data.get('started_at')
                    self.last_updated = data.get('last_updated')
                    print(f"Loaded state: {len(self.completed_files)} completed, "
                          f"{len(self.failed_files)} failed")
            except Exception as e:
                print(f"Warning: Could not load state file: {e}")
    
    def save_state(self):
        """Save current state to file"""
        try:
            data = {
                'completed_files': sorted(list(self.completed_files)),
                'failed_files': self.failed_files,
                'started_at': self.started_at,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save state: {e}")
    
    def mark_completed(self, file_path: str):
        """Mark a file as successfully completed"""
        self.completed_files.add(file_path)
        # Remove from failed if it was there
        if file_path in self.failed_files:
            del self.failed_files[file_path]
        self.save_state()
    
    def mark_failed(self, file_path: str, error: str):
        """Mark a file as failed"""
        self.failed_files[file_path] = error
        self.save_state()
    
    def is_completed(self, file_path: str) -> bool:
        """Check if file was already processed"""
        return file_path in self.completed_files
    
    def reset(self):
        """Clear all state"""
        self.completed_files.clear()
        self.failed_files.clear()
        self.started_at = datetime.now().isoformat()
        self.save_state()

class Orchestrator:
    """Production orchestrator with resume capability"""
    
    def __init__(self, entities: List[str] = None, resume: bool = True, 
                 retry_failed: bool = False):
        self.entities = entities or PROCESSING_ORDER
        self.resume = resume
        self.retry_failed = retry_failed
        
        # Setup state tracking
        self.state = ProcessingState()
        if not resume:
            print("Starting fresh - clearing previous state")
            self.state.reset()
        
        if not self.state.started_at:
            self.state.started_at = datetime.now().isoformat()
            self.state.save_state()
        
        # Setup logging in same directory as orchestrator
        self.log_dir = SCRIPT_DIR / 'logs'
        self.log_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = open(self.log_dir / f'orchestrator_{timestamp}.log', 'w')
        
        self.stats = {
            'total_files': 0,
            'completed': 0,
            'skipped': 0,
            'failed': 0,
            'retried': 0
        }
    
    def log(self, message: str, level: str = 'INFO'):
        """Log message to both console and file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        formatted = f"[{timestamp}] [{level:5s}] {message}"
        print(formatted)
        self.log_file.write(formatted + '\n')
        self.log_file.flush()
    
    def discover_files(self, entity: str) -> List[str]:
        """Find all .gz files for an entity"""
        entity_path = Path(DATA_ROOT) / entity
        if not entity_path.exists():
            return []
        
        files = []
        for date_dir in sorted(entity_path.glob('updated_date=*')):
            for gz_file in sorted(date_dir.glob('*.gz')):
                files.append(str(gz_file.absolute()))  # Full absolute path
        
        return files
    
    def test_database(self) -> bool:
        """Test database connection"""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            cursor.execute("SELECT version()")
            version = cursor.fetchone()[0]
            cursor.close()
            conn.close()
            self.log(f"Database connected: {version[:50]}...")
            return True
        except Exception as e:
            self.log(f"❌ Database connection failed: {e}", 'ERROR')
            return False
    
    def process_file(self, entity: str, file_path: str, file_num: int, 
                     total_files: int) -> bool:
        """Process a single file"""
        # Check if already completed (and not retrying)
        if self.resume and self.state.is_completed(file_path):
            if not (self.retry_failed and file_path in self.state.failed_files):
                self.log(f"[{file_num}/{total_files}] SKIP: {file_path} (already completed)")
                self.stats['skipped'] += 1
                return True
        
        # Check if previously failed and we're retrying
        if file_path in self.state.failed_files and self.retry_failed:
            self.log(f"[{file_num}/{total_files}] RETRY: {file_path}")
            self.stats['retried'] += 1
        else:
            self.log(f"[{file_num}/{total_files}] START: {file_path}")
        
        parser = PARSERS[entity]
        
        try:
            # Run parser with increased timeout for large files
            mode = 'update' if self.resume else 'clean'
            result = subprocess.run(
                [sys.executable, parser, '--input-file', file_path, '--mode', mode],
                capture_output=True,
                text=True,
                timeout=17200
            )
            
            if result.returncode == 0:
                self.log(f"  ✅ SUCCESS: {Path(file_path).name}")
                self.state.mark_completed(file_path)
                self.stats['completed'] += 1
                return True
            else:
                error = result.stderr[-500:] if result.stderr else "Unknown error"
                self.log(f"  ❌ FAILED: {error}", 'ERROR')
                self.state.mark_failed(file_path, error)
                self.stats['failed'] += 1
                return False
        
        except subprocess.TimeoutExpired:
            error = "Timeout after 2 hours"
            self.log(f"  ❌ TIMEOUT: {file_path}", 'ERROR')
            self.state.mark_failed(file_path, error)
            self.stats['failed'] += 1
            return False
            
        except KeyboardInterrupt:
            self.log("⚠️  Process interrupted by user - state saved", 'WARN')
            raise
            
        except Exception as e:
            error = str(e)
            self.log(f"  ❌ ERROR: {error}", 'ERROR')
            self.state.mark_failed(file_path, error)
            self.stats['failed'] += 1
            return False
    
    def process_entity(self, entity: str) -> bool:
        """Process all files for one entity"""
        self.log("=" * 80)
        self.log(f"ENTITY: {entity.upper()}")
        self.log("=" * 80)
        
        # Check parser exists
        parser = PARSERS.get(entity)
        if not parser or not Path(parser).exists():
            self.log(f"❌ Parser not found: {parser}", 'ERROR')
            return False
        
        # Discover files
        files = self.discover_files(entity)
        if not files:
            self.log(f"No files found for {entity}", 'WARN')
            return True
        
        # Filter files if resuming
        files_to_process = []
        for f in files:
            if not self.resume or not self.state.is_completed(f) or \
               (self.retry_failed and f in self.state.failed_files):
                files_to_process.append(f)
        
        self.log(f"Total files: {len(files)}")
        if self.resume:
            already_done = len(files) - len(files_to_process)
            self.log(f"✅ Already completed: {already_done}")
            self.log(f"To process: {len(files_to_process)}")
        
        if not files_to_process:
            self.log("✅ All files already processed")
            return True
        
        # Process files
        entity_success = 0
        entity_failed = 0
        self.stats['total_files'] += len(files_to_process)
        
        for i, file_path in enumerate(files_to_process, 1):
            success = self.process_file(entity, file_path, i, len(files_to_process))
            if success:
                entity_success += 1
            else:
                entity_failed += 1
        
        # Entity summary
        self.log("")
        self.log(f"{entity.upper()} SUMMARY:")
        self.log(f"  Processed: {entity_success + entity_failed}")
        self.log(f"  ✅ Success: {entity_success}")
        self.log(f"  âŒ Failed: {entity_failed}")
        
        return entity_failed == 0
    
    def generate_final_report(self, start_time: datetime):
        """Generate comprehensive final report"""
        duration = datetime.now() - start_time
        
        self.log("")
        self.log("=" * 80)
        self.log("FINAL REPORT")
        self.log("=" * 80)
        self.log(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"Ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"Duration: {duration}")
        self.log("")
        self.log(f"Entities processed: {len(self.entities)}")
        self.log(f"Total files: {self.stats['total_files']}")
        self.log(f"  ✅ Completed: {self.stats['completed']}")
        self.log(f"  ⏭️  Skipped: {self.stats['skipped']}")
        self.log(f"  ❌ Failed: {self.stats['failed']}")
        if self.retry_failed:
            self.log(f"  🔄 Retried: {self.stats['retried']}")
        
        # List failed files if any
        if self.state.failed_files:
            self.log("")
            self.log("❌ FAILED FILES:")
            for file_path, error in self.state.failed_files.items():
                self.log(f"  {file_path}")
                self.log(f"    Error: {error[:100]}")
        
        # Database counts
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor()
            self.log("")
            self.log("DATABASE RECORD COUNTS:")
            for entity in self.entities:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {entity}")
                    count = cursor.fetchone()[0]
                    self.log(f"  {entity:15s}: {count:,}")
                except:
                    pass
            cursor.close()
            conn.close()
        except:
            pass
        
        self.log("=" * 80)
        self.log(f"State file: {self.state.state_file}")
        self.log(f"Log file: {self.log_file.name}")
        
        if self.stats['failed'] > 0:
            self.log("")
            self.log(f"⚠️  ATTENTION: {self.stats['failed']} files failed", 'WARN')
            self.log("Re-run with --retry-failed to attempt failed files again")
    
    def run(self):
        """Main execution"""
        start_time = datetime.now()
        
        self.log("=" * 80)
        self.log("OPENALEX DATA INGESTION ORCHESTRATOR")
        self.log("=" * 80)
        self.log(f"Mode: {'RESUME' if self.resume else 'FRESH START'}")
        self.log(f"Entities: {', '.join(self.entities)}")
        self.log(f"Data root: {DATA_ROOT}")
        
        # Test database
        self.log("")
        if not self.test_database():
            self.log_file.close()
            return False
        
        # Process entities
        try:
            for entity in self.entities:
                self.process_entity(entity)
        
        except KeyboardInterrupt:
            self.log("")
            self.log("=" * 80)
            self.log("INTERRUPTED BY USER", 'WARN')
            self.log("=" * 80)
            self.log("State has been saved. Re-run without --no-resume to continue.")
            self.log_file.close()
            return False
        
        # Final report
        self.generate_final_report(start_time)
        self.log_file.close()
        
        return self.stats['failed'] == 0

def main():
    parser = argparse.ArgumentParser(
        description="Production OpenAlex Data Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Resume from where you left off (default)
  python small_orchestrator.py
  
  # Start fresh, clearing previous state
  python small_orchestrator.py --no-resume
  
  # Process specific entities only
  python small_orchestrator.py --entities topics concepts
  
  # Retry files that previously failed
  python small_orchestrator.py --retry-failed
  
  # Start fresh with specific entities
  python small_orchestrator.py --no-resume --entities sources institutions
        """
    )
    
    parser.add_argument('--entities', nargs='+', 
                       choices=list(PARSERS.keys()),
                       help="Specific entities to process (default: all in order)")
    
    parser.add_argument('--no-resume', dest='resume', action='store_false',
                       help="Start fresh, ignoring previous state")
    
    parser.add_argument('--retry-failed', action='store_true',
                       help="Retry files that previously failed")
    
    args = parser.parse_args()
    
    orchestrator = Orchestrator(
        entities=args.entities,
        resume=args.resume,
        retry_failed=args.retry_failed
    )
    
    success = orchestrator.run()
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
#!/usr/bin/env python3
"""
OpenAlex Authors Orchestrator
Loads all authors data into the database as quickly as possible
"""
import os
import sys
import subprocess
import json
import argparse
from pathlib import Path
from datetime import datetime
import psycopg2
from typing import List, Set

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from config import DB_CONFIG, DATA_ROOT

# Parser file mapping
PARSERS = {
    'authors': 'parse_authors.py'
}

STATE_FILE = 'orchestrator_state.json'

class ProcessingState:
    """Track completed files"""

    def __init__(self, state_file: str = STATE_FILE):
        self.state_file = state_file
        self.completed_files: Set[str] = set()
        self.load_state()

    def load_state(self):
        """Load existing state"""
        if Path(self.state_file).exists():
            try:
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    self.completed_files = set(data.get('completed_files', []))
                    print(f"Loaded state: {len(self.completed_files)} files completed")
            except Exception as e:
                print(f"Warning: Could not load state: {e}")

    def save_state(self):
        """Save current state"""
        try:
            data = {
                'completed_files': sorted(list(self.completed_files)),
                'last_updated': datetime.now().isoformat()
            }
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save state: {e}")

    def mark_completed(self, file_path: str):
        """Mark file as completed"""
        self.completed_files.add(file_path)
        self.save_state()

    def is_completed(self, file_path: str) -> bool:
        """Check if file completed"""
        return file_path in self.completed_files

    def reset(self):
        """Clear all state"""
        self.completed_files.clear()
        self.save_state()

class Orchestrator:
    """Orchestrator for Authors data loading"""

    def __init__(self, entities: List[str], resume: bool = True):
        self.entities = entities
        self.resume = resume

        # State tracking
        self.state = ProcessingState()
        if not resume:
            print("Starting fresh - clearing previous state")
            self.state.reset()

        # Setup logging
        self.log_dir = Path('logs')
        self.log_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = open(self.log_dir / f'orchestrator_{timestamp}.log', 'w')

        self.stats = {
            'total_files': 0,
            'completed': 0,
            'skipped': 0,
            'failed': 0
        }

    def log(self, message: str):
        """Log to console and file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        formatted = f"[{timestamp}] {message}"
        print(formatted)
        self.log_file.write(formatted + '\n')
        self.log_file.flush()

    def discover_files(self, entity: str) -> List[str]:
        """Find all .gz files for entity"""
        entity_path = Path(DATA_ROOT) / entity
        if not entity_path.exists():
            return []

        files = []
        for date_dir in sorted(entity_path.glob('updated_date=*')):
            for gz_file in sorted(date_dir.glob('*.gz')):
                files.append(str(gz_file.absolute()))

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
            self.log(f"ERROR: Database connection failed: {e}")
            return False

    def process_file(self, entity: str, file_path: str, file_num: int, total_files: int) -> bool:
        """Process a single file"""
        # Check if already completed
        if self.resume and self.state.is_completed(file_path):
            self.log(f"[{file_num}/{total_files}] ⏭️  SKIP: {file_path}")
            self.stats['skipped'] += 1
            return True

        self.log(f"[{file_num}/{total_files}] START: {file_path}")

        parser = PARSERS[entity]
        parser_path = Path(__file__).parent / parser

        try:
            # Run parser
            mode = 'update' if self.resume else 'clean'
            result = subprocess.run(
                [sys.executable, str(parser_path), '--input-file', file_path, '--mode', mode],
                capture_output=True,
                text=True,
                timeout=14400  # 24 hour timeout
            )

            if result.returncode == 0:
                self.log(f"[{file_num}/{total_files}] ✅ SUCCESS: {file_path}")
                self.state.mark_completed(file_path)
                self.stats['completed'] += 1
                return True
            else:
                error = result.stderr[-200:] if result.stderr else "Unknown error"
                self.log(f"[{file_num}/{total_files}] ❌ FAILED: {file_path}")
                self.log(f"  Error: {error}")
                self.stats['failed'] += 1
                return False

        except subprocess.TimeoutExpired:
            self.log(f"[{file_num}/{total_files}] ❌ TIMEOUT after 4 hours: {file_path}")
            self.stats['failed'] += 1
            return False

        except KeyboardInterrupt:
            self.log("⚠️  Interrupted by user - state saved")
            raise

        except Exception as e:
            self.log(f"[{file_num}/{total_files}] ❌ ERROR: {file_path}")
            self.log(f"  Exception: {e}")
            self.stats['failed'] += 1
            return False

    def process_entity(self, entity: str) -> bool:
        """Process all files for one entity"""
        self.log("=" * 80)
        self.log(f"ENTITY: {entity.upper()}")
        self.log("=" * 80)

        # Check parser exists
        parser = PARSERS.get(entity)
        parser_path = Path(__file__).parent / parser if parser else None
        if not parser or not parser_path.exists():
            self.log(f"ERROR: Parser not found: {parser_path}")
            return False

        # Discover files
        files = self.discover_files(entity)
        if not files:
            self.log(f"No files found for {entity}")
            return True

        # Filter already completed
        files_to_process = []
        for f in files:
            if not self.resume or not self.state.is_completed(f):
                files_to_process.append(f)

        self.log(f"Total files: {len(files)}")
        if self.resume:
            already_done = len(files) - len(files_to_process)
            self.log(f"Already completed: {already_done}")
            self.log(f"To process: {len(files_to_process)}")

        if not files_to_process:
            self.log("All files already processed")
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
        self.log(f"  Success: {entity_success}")
        self.log(f"  Failed: {entity_failed}")

        return entity_failed == 0

    def generate_final_report(self, start_time: datetime):
        """Generate final report"""
        duration = datetime.now() - start_time

        self.log("")
        self.log("=" * 80)
        self.log("FINAL REPORT - AUTHORS TABLE")
        self.log("=" * 80)
        self.log(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"Ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log(f"Duration: {duration}")
        self.log("")
        self.log(f"Entities processed: {len(self.entities)}")
        self.log(f"Total files: {self.stats['total_files']}")
        self.log(f"  Completed: {self.stats['completed']}")
        self.log(f"  Skipped: {self.stats['skipped']}")
        self.log(f"  Failed: {self.stats['failed']}")

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

        if self.stats['failed'] > 0:
            self.log(f"WARNING: {self.stats['failed']} files failed")
        else:
            self.log("")
            self.log("AUTHORS TABLE LOADED SUCCESSFULLY")

    def run(self):
        """Main execution"""
        start_time = datetime.now()

        self.log("=" * 80)
        self.log("OPENALEX AUTHORS ORCHESTRATOR")
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
            self.log("INTERRUPTED BY USER")
            self.log("=" * 80)
            self.log("State saved. Re-run to continue.")
            self.log_file.close()
            return False

        # Final report
        self.generate_final_report(start_time)
        self.log_file.close()

        return self.stats['failed'] == 0

def main():
    parser = argparse.ArgumentParser(
        description="OpenAlex Authors Orchestrator - Fast bulk loading of authors data",
        epilog="""
Examples:
  # Resume from where you left off (default)
  python authors_orchestrator.py

  # Start fresh
  python authors_orchestrator.py --no-resume
        """
    )

    parser.add_argument('--no-resume', dest='resume', action='store_false',
                       help="Start fresh, ignoring previous state")

    args = parser.parse_args()

    # Only process authors
    orchestrator = Orchestrator(
        entities=['authors'],
        resume=args.resume
    )

    success = orchestrator.run()
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()

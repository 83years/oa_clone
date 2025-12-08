#!/usr/bin/env python3
"""
Smart orchestrator for OpenAlex parsing pipeline
Manages parsing order, tracks state, logs issues, provides real-time info
"""
import json
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path
import subprocess

# Add parent to path
SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent
sys.path.insert(0, str(PARENT_DIR))

from config import GZ_DIRECTORIES, LOG_DIR
import glob

# State file
STATE_FILE = SCRIPT_DIR / 'orchestrator_state.json'


class Orchestrator:
    """Manages the parsing pipeline"""

    def __init__(self, line_limit=None, test_mode=False):
        """
        Initialize orchestrator

        Args:
            line_limit: Limit lines per file (for testing)
            test_mode: Run in test mode with 100k line limit
        """
        self.line_limit = line_limit
        if test_mode:
            self.line_limit = 100000

        self.state = self.load_state()
        self.log_path = f"{LOG_DIR}/orchestrator.log"

    def load_state(self):
        """Load orchestrator state from JSON file"""
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                # Ensure all entities have completed_files list
                for entity in state:
                    if 'completed_files' not in state[entity]:
                        state[entity]['completed_files'] = []
                return state
        else:
            return {
                'topics': {'status': 'pending', 'records': 0, 'errors': 0, 'completed_files': []},
                'concepts': {'status': 'pending', 'records': 0, 'errors': 0, 'completed_files': []},
                'publishers': {'status': 'pending', 'records': 0, 'errors': 0, 'completed_files': []},
                'funders': {'status': 'pending', 'records': 0, 'errors': 0, 'completed_files': []},
                'sources': {'status': 'pending', 'records': 0, 'errors': 0, 'completed_files': []},
                'institutions': {'status': 'pending', 'records': 0, 'errors': 0, 'completed_files': []},
                'authors': {'status': 'pending', 'records': 0, 'errors': 0, 'completed_files': []},
                'works': {'status': 'pending', 'records': 0, 'errors': 0, 'completed_files': []},
                'authorship': {'status': 'pending', 'records': 0, 'errors': 0, 'completed_files': []}
            }

    def save_state(self):
        """Save current state to JSON file"""
        with open(STATE_FILE, 'w') as f:
            json.dump(self.state, f, indent=2)

    def log(self, message):
        """Log message to file and console"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] {message}"
        print(log_msg)
        with open(self.log_path, 'a') as f:
            f.write(log_msg + '\n')

    def get_gz_files(self, entity_directory):
        """
        Get all part_*.gz files from all updated_date=* subdirectories

        Args:
            entity_directory: Path to entity directory (e.g., /path/to/topics)

        Returns:
            list: Sorted list of .gz file paths from all dated subdirectories
        """
        if not Path(entity_directory).exists():
            self.log(f"⚠️  Directory not found: {entity_directory}")
            return []

        all_files = []

        # Find all updated_date=* subdirectories
        entity_path = Path(entity_directory)
        dated_dirs = sorted(entity_path.glob('updated_date=*'))

        if not dated_dirs:
            self.log(f"⚠️  No updated_date=* subdirectories found in {entity_directory}")
            return []

        self.log(f"Found {len(dated_dirs)} dated folder(s):")
        for dated_dir in dated_dirs:
            self.log(f"  - {dated_dir.name}")

        # Collect all part_*.gz files from all dated directories
        for dated_dir in dated_dirs:
            pattern = str(dated_dir / 'part_*.gz')
            files = sorted(glob.glob(pattern))
            all_files.extend(files)

        if not all_files:
            self.log(f"⚠️  No .gz files found in any dated subdirectory")
        else:
            self.log(f"Total .gz files to process: {len(all_files)}")

        return sorted(all_files)

    def run_parser(self, entity_name, parser_script, entity_directory):
        """
        Run a parser script on all .gz files from all dated subdirectories

        Args:
            entity_name: Name of entity (e.g., 'topics')
            parser_script: Path to parser script
            entity_directory: Path to entity directory (will process all updated_date=* subdirs)

        Returns:
            bool: True if successful, False otherwise
        """
        self.log(f"\n{'='*70}")
        self.log(f"PARSING: {entity_name.upper()}")
        self.log(f"{'='*70}")

        # Get all .gz files from all dated subdirectories
        gz_files = self.get_gz_files(entity_directory)
        if not gz_files:
            self.log(f"❌ No files found in {entity_directory}")
            self.state[entity_name]['status'] = 'failed'
            self.save_state()
            return False

        # Get list of completed files for this entity
        completed_files = set(self.state[entity_name].get('completed_files', []))

        # Filter out already completed files
        files_to_process = [f for f in gz_files if f not in completed_files]

        if completed_files:
            self.log(f"Found {len(completed_files)} already completed file(s)")
            self.log(f"Remaining files to process: {len(files_to_process)}")

        if not files_to_process:
            self.log(f"✅ All files already processed for {entity_name}")
            self.state[entity_name]['status'] = 'complete'
            if 'completed' not in self.state[entity_name]:
                self.state[entity_name]['completed'] = datetime.now().isoformat()
            self.save_state()
            return True

        self.log(f"Found {len(gz_files)} total file(s), {len(files_to_process)} to process:")
        for gz_file in files_to_process[:10]:  # Show first 10
            self.log(f"  - {Path(gz_file).name}")
        if len(files_to_process) > 10:
            self.log(f"  ... and {len(files_to_process) - 10} more")

        # Update state
        self.state[entity_name]['status'] = 'running'
        if 'started' not in self.state[entity_name]:
            self.state[entity_name]['started'] = datetime.now().isoformat()
        self.save_state()

        overall_start = time.time()

        # Process each file
        for i, gz_file in enumerate(files_to_process, 1):
            # Calculate actual position in full list
            actual_position = gz_files.index(gz_file) + 1
            self.log(f"\n--- Processing file {actual_position}/{len(gz_files)}: {Path(gz_file).name} ---")

            # Build command
            cmd = [sys.executable, str(parser_script), '--input-file', gz_file]
            if self.line_limit:
                cmd.extend(['--limit', str(self.line_limit)])

            self.log(f"Command: {' '.join(cmd)}")

            # Run parser
            try:
                start_time = time.time()
                result = subprocess.run(cmd, capture_output=True, text=True)

                # Log output
                if result.stdout:
                    self.log(result.stdout)
                if result.stderr:
                    self.log(f"STDERR: {result.stderr}")

                elapsed = time.time() - start_time

                if result.returncode == 0:
                    self.log(f"✅ File {actual_position}/{len(gz_files)} completed successfully in {elapsed:.1f}s")

                    # Mark file as completed and save state
                    self.state[entity_name]['completed_files'].append(gz_file)
                    self.save_state()
                else:
                    self.log(f"❌ File {actual_position}/{len(gz_files)} failed with return code {result.returncode}")
                    self.state[entity_name]['status'] = 'failed'
                    self.state[entity_name]['completed'] = datetime.now().isoformat()
                    self.save_state()
                    return False

            except Exception as e:
                self.log(f"❌ Exception processing file {actual_position}/{len(gz_files)}: {e}")
                self.state[entity_name]['status'] = 'failed'
                self.save_state()
                return False

        # All files processed successfully
        overall_elapsed = time.time() - overall_start
        self.log(f"\n✅ {entity_name} - All {len(gz_files)} file(s) completed successfully in {overall_elapsed:.1f}s")
        self.state[entity_name]['status'] = 'complete'
        self.state[entity_name]['completed'] = datetime.now().isoformat()
        self.save_state()
        return True

    def print_status(self):
        """Print current status of all parsers"""
        self.log(f"\n{'='*70}")
        self.log("ORCHESTRATOR STATUS")
        self.log(f"{'='*70}")

        for entity, state in self.state.items():
            status = state.get('status', 'unknown')
            records = state.get('records', 0)
            errors = state.get('errors', 0)
            completed_files = len(state.get('completed_files', []))

            if status == 'complete':
                icon = '✅'
            elif status == 'running':
                icon = '⏳'
            elif status == 'failed':
                icon = '❌'
            else:
                icon = '⏸️ '

            self.log(f"  {icon} {entity:15s} {status:10s} | Files: {completed_files:,} | Records: {records:,} | Errors: {errors}")

        self.log(f"{'='*70}\n")

    def run_all(self):
        """Run all parsers in dependency order"""
        self.log(f"\n{'#'*70}")
        self.log("STARTING OPENALEX PARSING PIPELINE")
        if self.line_limit:
            self.log(f"TEST MODE: Processing {self.line_limit:,} lines per file")
        else:
            self.log("PRODUCTION MODE: Processing all records")
        self.log(f"{'#'*70}\n")

        pipeline_start = time.time()

        # Phase 1: Small reference tables
        phase1 = [
            ('topics', 'parse_topics_v2.py', GZ_DIRECTORIES.get('topics')),
            ('concepts', 'parse_concepts_v2.py', GZ_DIRECTORIES.get('concepts')),
            ('publishers', 'parse_publishers_v2.py', GZ_DIRECTORIES.get('publishers')),
            ('funders', 'parse_funders_v2.py', GZ_DIRECTORIES.get('funders')),
        ]

        self.log("PHASE 1: Reference tables (topics, concepts, publishers, funders)")
        for entity, script, gz_dir in phase1:
            if self.state[entity]['status'] in ['complete']:
                self.log(f"Skipping {entity} (already {self.state[entity]['status']})")
                continue

            script_path = SCRIPT_DIR / script
            if not script_path.exists():
                self.log(f"⚠️  Parser script not found: {script_path}")
                continue

            success = self.run_parser(entity, script_path, gz_dir)
            if not success:
                self.log(f"❌ Pipeline halted due to {entity} failure")
                return False

        # Phase 2: Sources and Institutions
        phase2 = [
            ('sources', 'parse_sources_v2.py', GZ_DIRECTORIES.get('sources')),
            ('institutions', 'parse_institutions_v2.py', GZ_DIRECTORIES.get('institutions')),
        ]

        self.log("\nPHASE 2: Sources and Institutions")
        for entity, script, gz_dir in phase2:
            if self.state[entity]['status'] in ['complete']:
                self.log(f"Skipping {entity} (already {self.state[entity]['status']})")
                continue

            script_path = SCRIPT_DIR / script
            if not script_path.exists():
                self.log(f"⚠️  Parser script not found: {script_path}")
                continue

            success = self.run_parser(entity, script_path, gz_dir)
            if not success:
                self.log(f"❌ Pipeline halted due to {entity} failure")
                return False

        # Phase 3: Authors (large, depends on institutions)
        self.log("\nPHASE 3: Authors")
        entity = 'authors'
        script = 'parse_authors_v2.py'
        gz_directory = GZ_DIRECTORIES.get('authors')

        if self.state[entity]['status'] not in ['complete']:
            script_path = SCRIPT_DIR / script
            if script_path.exists():
                success = self.run_parser(entity, script_path, gz_directory)
                if not success:
                    self.log(f"❌ Pipeline halted due to {entity} failure")
                    return False
            else:
                self.log(f"⚠️  Parser script not found: {script_path}")

        # Phase 4: Works (huge, includes authorship)
        self.log("\nPHASE 4: Works (includes authorship)")
        entity = 'works'
        script = 'parse_works_v2.py'
        gz_directory = GZ_DIRECTORIES.get('works')

        if self.state[entity]['status'] not in ['complete']:
            script_path = SCRIPT_DIR / script
            if script_path.exists():
                success = self.run_parser(entity, script_path, gz_directory)
                if not success:
                    self.log(f"❌ Pipeline halted due to {entity} failure")
                    return False
            else:
                self.log(f"⚠️  Parser script not found: {script_path}")

        # Final summary
        pipeline_elapsed = time.time() - pipeline_start
        self.log(f"\n{'#'*70}")
        self.log(f"PIPELINE COMPLETE - Total time: {pipeline_elapsed:.1f}s")
        self.log(f"{'#'*70}\n")

        self.print_status()

        return True

    def reset(self):
        """Reset orchestrator state"""
        self.log("Resetting orchestrator state...")
        if STATE_FILE.exists():
            STATE_FILE.unlink()
        self.state = self.load_state()
        self.log("✅ State reset complete")

    def clear_entity_files(self, entity_name):
        """Clear completed files for a specific entity"""
        if entity_name in self.state:
            self.state[entity_name]['completed_files'] = []
            self.state[entity_name]['status'] = 'pending'
            self.save_state()
            self.log(f"✅ Cleared completed files for {entity_name}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='OpenAlex Parsing Orchestrator')
    parser.add_argument('--start', action='store_true', help='Start parsing from beginning (clears incomplete file tracking)')
    parser.add_argument('--resume', action='store_true', help='Resume from saved state (preserves file tracking)')
    parser.add_argument('--status', action='store_true', help='Show current status')
    parser.add_argument('--reset', action='store_true', help='Reset all state')
    parser.add_argument('--clear-entity', type=str, help='Clear completed files for specific entity')
    parser.add_argument('--test', action='store_true', help='Test mode (100k lines per file)')
    parser.add_argument('--limit', type=int, help='Custom line limit per file')

    args = parser.parse_args()

    orchestrator = Orchestrator(
        line_limit=args.limit,
        test_mode=args.test
    )

    if args.status:
        orchestrator.print_status()
    elif args.reset:
        orchestrator.reset()
    elif args.clear_entity:
        orchestrator.clear_entity_files(args.clear_entity)
    elif args.start:
        # Clear file tracking for incomplete entities
        orchestrator.log("Starting from beginning - clearing file tracking for incomplete entities")
        for entity in orchestrator.state:
            if orchestrator.state[entity]['status'] != 'complete':
                orchestrator.state[entity]['completed_files'] = []
        orchestrator.save_state()
        orchestrator.run_all()
    elif args.resume:
        orchestrator.run_all()
    else:
        parser.print_help()

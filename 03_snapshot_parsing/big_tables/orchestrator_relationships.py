#!/usr/bin/env python3
"""
Phase 2 Orchestrator - Extract and Load Work Relationships
Coordinates extraction from works files and loading into joining tables
"""
import os
import sys
import subprocess
import json
import argparse
from pathlib import Path
from datetime import datetime

from config import DATA_ROOT

CSV_OUTPUT_DIR = Path('/Volumes/OA_snapshot/works_tables')
STATE_FILE = 'phase2_state.json'

# Table loading order (sequential for easier debugging)
LOADING_ORDER = [
    'authorship',          # Critical: author-work links
    'work_topics',         # Critical: subject classification
    'work_concepts',       # Important: concept analysis
    'work_sources',        # Important: journal/venue links
    'citations_by_year',   # Important: temporal citations
    'referenced_works',    # Important: citations/references
    'work_funders',        # Medium: grant relationships
    'alternate_ids',       # Medium: alternate identifiers
    'work_keywords',       # Medium: keywords
    'related_works',       # Low: related works
    'apc',                 # Low: APC data
]

class Phase2Orchestrator:
    """Orchestrate Phase 2: Relationship extraction and loading"""

    def __init__(self, resume: bool = True):
        self.resume = resume
        self.state = self.load_state()

        # Setup logging
        self.log_dir = Path('logs')
        self.log_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.log_file = open(self.log_dir / f'phase2_orchestrator_{timestamp}.log', 'w')

        self.stats = {
            'extraction': {
                'started': None,
                'completed': None,
                'files_processed': 0,
                'files_failed': 0
            },
            'loading': {
                'started': None,
                'completed': None,
                'tables_loaded': {},
                'tables_failed': []
            }
        }

    def log(self, message: str):
        """Log to console and file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        formatted = f"[{timestamp}] {message}"
        print(formatted)
        self.log_file.write(formatted + '\n')
        self.log_file.flush()

    def load_state(self):
        """Load processing state"""
        if Path(STATE_FILE).exists():
            with open(STATE_FILE, 'r') as f:
                state = json.load(f)
                self.log(f"Loaded state from {STATE_FILE}")
                return state
        return {
            'phase': 'not_started',
            'extraction': {
                'completed_files': [],
                'failed_files': []
            },
            'loading': {
                'completed_tables': [],
                'failed_tables': []
            }
        }

    def save_state(self):
        """Save processing state"""
        with open(STATE_FILE, 'w') as f:
            json.dump(self.state, f, indent=2)

    def discover_works_files(self):
        """Find all works .gz files"""
        self.log("Discovering works files...")
        works_path = Path(DATA_ROOT) / 'works'

        if not works_path.exists():
            self.log(f"❌ ERROR: Works directory not found: {works_path}")
            return []

        files = []
        for date_dir in sorted(works_path.glob('updated_date=*')):
            for gz_file in sorted(date_dir.glob('*.gz')):
                files.append(str(gz_file.absolute()))

        self.log(f"  Found {len(files):,} works files")
        return files

    def run_extraction(self):
        """Phase 2a: Extract relationships to CSV"""
        self.log("=" * 80)
        self.log("PHASE 2a: EXTRACTING RELATIONSHIPS TO CSV")
        self.log("=" * 80)

        self.stats['extraction']['started'] = datetime.now().isoformat()

        # Find all works files
        works_files = self.discover_works_files()
        if not works_files:
            self.log("❌ ERROR: No works files found")
            return False

        # Filter already completed
        if self.resume:
            completed = set(self.state['extraction']['completed_files'])
            works_files = [f for f in works_files if f not in completed]
            self.log(f"  Resuming: {len(works_files):,} files remaining")

        if not works_files:
            self.log("  ✅ All files already extracted")
            return True

        # Create CSV output directory
        CSV_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        # Process each file
        for i, file_path in enumerate(works_files, 1):
            self.log(f"\n[{i}/{len(works_files)}] Extracting: {Path(file_path).name}")

            try:
                result = subprocess.run(
                    [sys.executable, 'parse_works_relationships.py',
                     '--input-file', file_path,
                     '--output-dir', str(CSV_OUTPUT_DIR)],
                    capture_output=True,
                    text=True,
                    timeout=7200  # 2 hour timeout
                )

                if result.returncode == 0:
                    self.log(f"  ✅ SUCCESS")
                    self.state['extraction']['completed_files'].append(file_path)
                    self.stats['extraction']['files_processed'] += 1
                else:
                    error = result.stderr[-200:] if result.stderr else "Unknown error"
                    self.log(f"  ❌ FAILED: {error}")
                    self.state['extraction']['failed_files'].append(file_path)
                    self.stats['extraction']['files_failed'] += 1

                self.save_state()

            except subprocess.TimeoutExpired:
                self.log(f"  ❌ TIMEOUT after 2 hours")
                self.state['extraction']['failed_files'].append(file_path)
                self.stats['extraction']['files_failed'] += 1
                self.save_state()

            except KeyboardInterrupt:
                self.log("\n⚠️  Interrupted by user - state saved")
                self.save_state()
                raise

            except Exception as e:
                self.log(f"  ❌ ERROR: {e}")
                self.state['extraction']['failed_files'].append(file_path)
                self.stats['extraction']['files_failed'] += 1
                self.save_state()

        self.stats['extraction']['completed'] = datetime.now().isoformat()
        self.state['phase'] = 'extraction_complete'
        self.save_state()

        # Report
        self.log("\n" + "=" * 80)
        self.log("EXTRACTION SUMMARY")
        self.log("=" * 80)
        self.log(f"  ✅ Successful: {self.stats['extraction']['files_processed']:,}")
        self.log(f"  ❌ Failed: {self.stats['extraction']['files_failed']:,}")

        return self.stats['extraction']['files_failed'] == 0

    def run_loading(self):
        """Phase 2b: Load CSVs into database tables"""
        self.log("\n" + "=" * 80)
        self.log("PHASE 2b: LOADING CSV INTO DATABASE TABLES")
        self.log("=" * 80)

        self.stats['loading']['started'] = datetime.now().isoformat()

        # Filter already completed tables
        if self.resume:
            completed = set(self.state['loading']['completed_tables'])
            tables_to_load = [t for t in LOADING_ORDER if t not in completed]
            self.log(f"  Resuming: {len(tables_to_load)} tables remaining")
        else:
            tables_to_load = LOADING_ORDER

        if not tables_to_load:
            self.log("  ✅ All tables already loaded")
            return True

        # Load each table sequentially
        for i, table_name in enumerate(tables_to_load, 1):
            self.log(f"\n[{i}/{len(tables_to_load)}] Loading table: {table_name}")
            self.log("=" * 60)

            try:
                result = subprocess.run(
                    [sys.executable, 'load_relationships.py',
                     '--table', table_name,
                     '--csv-dir', str(CSV_OUTPUT_DIR),
                     '--threshold', '0.01'],  # 1% FK violation threshold
                    capture_output=True,
                    text=True,
                    timeout=14400  # 4 hour timeout
                )

                if result.returncode == 0:
                    self.log(f"  ✅ SUCCESS: {table_name}")
                    self.state['loading']['completed_tables'].append(table_name)
                    self.stats['loading']['tables_loaded'][table_name] = 'success'
                else:
                    error = result.stderr[-500:] if result.stderr else "Unknown error"
                    self.log(f"  ❌ FAILED: {table_name}")
                    self.log(f"     Error: {error}")
                    self.state['loading']['failed_tables'].append(table_name)
                    self.stats['loading']['tables_loaded'][table_name] = 'failed'

                    # Ask user if they want to continue
                    response = input("\nTable failed. Continue with remaining tables? (yes/no): ")
                    if response.lower() != 'yes':
                        self.log("❌ Aborted by user")
                        self.save_state()
                        return False

                self.save_state()

            except subprocess.TimeoutExpired:
                self.log(f"  ❌ TIMEOUT: {table_name} after 4 hours")
                self.state['loading']['failed_tables'].append(table_name)
                self.stats['loading']['tables_loaded'][table_name] = 'timeout'
                self.save_state()

                response = input("\nTable timed out. Continue with remaining tables? (yes/no): ")
                if response.lower() != 'yes':
                    return False

            except KeyboardInterrupt:
                self.log("\n⚠️  Interrupted by user - state saved")
                self.save_state()
                raise

            except Exception as e:
                self.log(f"  ❌ ERROR: {table_name}: {e}")
                self.state['loading']['failed_tables'].append(table_name)
                self.stats['loading']['tables_loaded'][table_name] = 'error'
                self.save_state()

        self.stats['loading']['completed'] = datetime.now().isoformat()
        self.state['phase'] = 'loading_complete'
        self.save_state()

        # Report
        self.log("\n" + "=" * 80)
        self.log("LOADING SUMMARY")
        self.log("=" * 80)
        for table_name, status in self.stats['loading']['tables_loaded'].items():
            icon = "✅" if status == "success" else "❌"
            self.log(f"  {icon} {table_name:20s}: {status}")

        failed_count = len(self.state['loading']['failed_tables'])
        return failed_count == 0

    def generate_final_report(self):
        """Generate comprehensive final report"""
        self.log("\n" + "=" * 80)
        self.log("PHASE 2 FINAL REPORT")
        self.log("=" * 80)

        # Extraction summary
        self.log("\nEXTRACTION:")
        if self.stats['extraction']['started']:
            self.log(f"  Started: {self.stats['extraction']['started']}")
            self.log(f"  Completed: {self.stats['extraction']['completed']}")
            self.log(f"  Files processed: {self.stats['extraction']['files_processed']:,}")
            self.log(f"  Files failed: {self.stats['extraction']['files_failed']:,}")
        else:
            self.log("  Not started")

        # Loading summary
        self.log("\nLOADING:")
        if self.stats['loading']['started']:
            self.log(f"  Started: {self.stats['loading']['started']}")
            self.log(f"  Completed: {self.stats['loading']['completed']}")
            self.log(f"  Tables loaded: {len(self.state['loading']['completed_tables'])}")
            self.log(f"  Tables failed: {len(self.state['loading']['failed_tables'])}")

            if self.state['loading']['failed_tables']:
                self.log(f"\n  Failed tables:")
                for table in self.state['loading']['failed_tables']:
                    self.log(f"    - {table}")
        else:
            self.log("  Not started")

        # Overall status
        self.log("\n" + "=" * 80)
        if self.state['phase'] == 'loading_complete' and not self.state['loading']['failed_tables']:
            self.log("✅ PHASE 2 COMPLETE - ALL JOINING TABLES LOADED")
        else:
            self.log("⚠️  PHASE 2 INCOMPLETE - REVIEW ERRORS ABOVE")
        self.log("=" * 80)

        # Save final stats
        with open('phase2_final_report.json', 'w') as f:
            json.dump({
                'state': self.state,
                'stats': self.stats
            }, f, indent=2)
        self.log("\nFull report saved to: phase2_final_report.json")

    def run(self):
        """Main orchestration"""
        start_time = datetime.now()

        self.log("=" * 80)
        self.log("PHASE 2 ORCHESTRATOR: WORK RELATIONSHIPS")
        self.log("=" * 80)
        self.log(f"Mode: {'RESUME' if self.resume else 'FRESH START'}")
        self.log(f"CSV output: {CSV_OUTPUT_DIR}")
        self.log(f"Current phase: {self.state.get('phase', 'not_started')}")

        try:
            # Phase 2a: Extraction
            if self.state['phase'] in ['not_started', 'extraction_in_progress']:
                self.state['phase'] = 'extraction_in_progress'
                self.save_state()

                extraction_success = self.run_extraction()

                if not extraction_success:
                    self.log("\n⚠️  WARNING: Some extraction files failed")
                    self.log("Review errors and re-run to retry failed files")

            # Phase 2b: Loading
            if self.state['phase'] in ['extraction_complete', 'loading_in_progress']:
                self.state['phase'] = 'loading_in_progress'
                self.save_state()

                loading_success = self.run_loading()

                if not loading_success:
                    self.log("\n⚠️  WARNING: Some tables failed to load")
                    self.log("Review errors and re-run to retry failed tables")

            # Final report
            self.generate_final_report()

            duration = datetime.now() - start_time
            self.log(f"\nTotal duration: {duration}")

            return self.state['phase'] == 'loading_complete'

        except KeyboardInterrupt:
            self.log("\n" + "=" * 80)
            self.log("INTERRUPTED BY USER")
            self.log("=" * 80)
            self.log("State saved. Re-run with --resume to continue.")
            return False

        finally:
            self.log_file.close()

def main():
    parser = argparse.ArgumentParser(
        description="Phase 2 Orchestrator - Extract and load work relationships",
        epilog="""
Examples:
  # Start fresh
  python3 orchestrator_relationships.py --no-resume

  # Resume from where you left off
  python3 orchestrator_relationships.py
        """
    )

    parser.add_argument('--no-resume', dest='resume', action='store_false',
                       help="Start fresh, ignoring previous state")

    args = parser.parse_args()

    orchestrator = Phase2Orchestrator(resume=args.resume)
    success = orchestrator.run()

    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()

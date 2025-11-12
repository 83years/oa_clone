#!/usr/bin/env python3
"""
Constraint Building Orchestrator for OpenAlex Database
Manages: Merged IDs → Orphan Analysis → Primary Keys → Indexes → Foreign Keys → Validation
"""
import json
import sys
import time
import argparse
from datetime import datetime
from pathlib import Path
import subprocess

SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PARENT_DIR))

from config import DB_CONFIG, LOG_DIR

STATE_FILE = SCRIPT_DIR / 'constraint_state.json'
LOG_FILE = SCRIPT_DIR / 'logs' / 'constraints.log'

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


class ConstraintOrchestrator:
    """Manages the constraint building pipeline"""

    def __init__(self, test_mode=False):
        """
        Initialize constraint orchestrator

        Args:
            test_mode: Use test database clone (oadb2_test)
        """
        self.test_mode = test_mode
        self.db_name = 'OADB_test' if test_mode else 'OADB'
        self.state = self.load_state()

    def load_state(self):
        """Load orchestrator state from JSON file"""
        if STATE_FILE.exists():
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        else:
            return {
                'merged_ids': {'status': 'pending', 'started': None, 'completed': None},
                'orphan_analysis': {'status': 'pending', 'started': None, 'completed': None},
                'primary_keys': {'status': 'pending', 'started': None, 'completed': None},
                'indexes': {'status': 'pending', 'started': None, 'completed': None},
                'foreign_keys': {'status': 'pending', 'started': None, 'completed': None},
                'validation': {'status': 'pending', 'started': None, 'completed': None},
                'reporting': {'status': 'pending', 'started': None, 'completed': None}
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
        with open(LOG_FILE, 'a') as f:
            f.write(log_msg + '\n')

    def run_script(self, phase_name, script_name):
        """
        Run a constraint building script

        Args:
            phase_name: Name of phase (e.g., 'merged_ids')
            script_name: Script filename (e.g., 'apply_merged_ids.py')

        Returns:
            bool: True if successful, False otherwise
        """
        self.log(f"\n{'='*70}")
        self.log(f"PHASE: {phase_name.upper().replace('_', ' ')}")
        self.log(f"{'='*70}")

        script_path = SCRIPT_DIR / script_name
        if not script_path.exists():
            self.log(f"⚠️  Script not found: {script_path}")
            self.log(f"Skipping {phase_name}")
            return True

        self.state[phase_name]['status'] = 'running'
        self.state[phase_name]['started'] = datetime.now().isoformat()
        self.save_state()

        cmd = [sys.executable, str(script_path)]
        if self.test_mode:
            cmd.append('--test')

        self.log(f"Command: {' '.join(cmd)}")

        try:
            start_time = time.time()
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.stdout:
                self.log(result.stdout)
            if result.stderr:
                self.log(f"STDERR: {result.stderr}")

            elapsed = time.time() - start_time

            if result.returncode == 0:
                self.log(f"✅ {phase_name} completed successfully in {elapsed:.1f}s")
                self.state[phase_name]['status'] = 'complete'
                self.state[phase_name]['completed'] = datetime.now().isoformat()
                self.save_state()
                return True
            else:
                self.log(f"❌ {phase_name} failed with return code {result.returncode}")
                self.state[phase_name]['status'] = 'failed'
                self.state[phase_name]['completed'] = datetime.now().isoformat()
                self.save_state()
                return False

        except Exception as e:
            self.log(f"❌ Exception running {phase_name}: {e}")
            self.state[phase_name]['status'] = 'failed'
            self.save_state()
            return False

    def print_status(self):
        """Print current status of all phases"""
        self.log(f"\n{'='*70}")
        self.log("CONSTRAINT BUILDING STATUS")
        self.log(f"Database: {self.db_name}")
        self.log(f"{'='*70}")

        for phase, state in self.state.items():
            status = state.get('status', 'unknown')

            if status == 'complete':
                icon = '✅'
            elif status == 'running':
                icon = '⏳'
            elif status == 'failed':
                icon = '❌'
            else:
                icon = '⏸️'

            phase_display = phase.replace('_', ' ').title()
            self.log(f"  {icon} {phase_display:20s} {status:10s}")

        self.log(f"{'='*70}\n")

    def run_all(self):
        """Run all constraint building phases in order"""
        self.log(f"\n{'#'*70}")
        self.log("STARTING CONSTRAINT BUILDING PIPELINE")
        self.log(f"Database: {self.db_name}")
        if self.test_mode:
            self.log("TEST MODE: Using database clone")
        else:
            self.log("PRODUCTION MODE: Modifying production database")
        self.log(f"{'#'*70}\n")

        pipeline_start = time.time()

        phases = [
            ('merged_ids', 'apply_merged_ids.py'),
            ('orphan_analysis', 'analyze_orphans.py'),
            ('primary_keys', 'add_primary_keys.py'),
            ('indexes', 'add_indexes.py'),
            ('foreign_keys', 'add_foreign_keys.py'),
            ('validation', 'validate_constraints.py'),
            ('reporting', 'generate_report.py')
        ]

        for phase_name, script_name in phases:
            if self.state[phase_name]['status'] in ['complete']:
                self.log(f"Skipping {phase_name} (already {self.state[phase_name]['status']})")
                continue

            success = self.run_script(phase_name, script_name)
            if not success:
                self.log(f"❌ Pipeline halted due to {phase_name} failure")
                return False

        pipeline_elapsed = time.time() - pipeline_start
        self.log(f"\n{'#'*70}")
        self.log(f"PIPELINE COMPLETE - Total time: {pipeline_elapsed:.1f}s ({pipeline_elapsed/3600:.1f} hours)")
        self.log(f"{'#'*70}\n")

        self.print_status()
        return True

    def reset(self):
        """Reset orchestrator state"""
        self.log("Resetting constraint orchestrator state...")
        if STATE_FILE.exists():
            STATE_FILE.unlink()
        self.state = self.load_state()
        self.log("✅ State reset complete")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='OpenAlex Constraint Building Orchestrator')
    parser.add_argument('--start', action='store_true', help='Start constraint building from beginning')
    parser.add_argument('--resume', action='store_true', help='Resume from saved state')
    parser.add_argument('--status', action='store_true', help='Show current status')
    parser.add_argument('--reset', action='store_true', help='Reset state')
    parser.add_argument('--test', action='store_true', help='Test mode (use oadb2_test database)')

    args = parser.parse_args()

    orchestrator = ConstraintOrchestrator(test_mode=args.test)

    if args.status:
        orchestrator.print_status()
    elif args.reset:
        orchestrator.reset()
    elif args.start or args.resume:
        orchestrator.run_all()
    else:
        parser.print_help()

#!/usr/bin/env python3
"""
Validate Foreign Key Constraints in OpenAlex Database
Validates all FKs created with NOT VALID flag
Logs validation failures for orphan retrieval via API
"""
import sys
from pathlib import Path
from datetime import datetime
import psycopg2
import argparse
import time

SCRIPT_DIR = Path(__file__).parent
PARENT_DIR = SCRIPT_DIR.parent.parent
sys.path.insert(0, str(PARENT_DIR))

from config import DB_CONFIG

VALIDATION_LOG = SCRIPT_DIR / 'logs' / 'validation_failures.log'
VALIDATION_LOG.parent.mkdir(parents=True, exist_ok=True)


class ConstraintValidator:
    """Validates NOT VALID foreign key constraints"""

    def __init__(self, test_mode=False):
        """
        Initialize constraint validator

        Args:
            test_mode: Use test database (oadb2_test)
        """
        self.test_mode = test_mode
        db_config = DB_CONFIG.copy()
        db_config['database'] = 'oadbv5_test' if test_mode else 'oadbv5'

        self.conn = psycopg2.connect(**db_config)
        self.conn.autocommit = False
        self.cursor = self.conn.cursor()

        # Set up file logging
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)
        self.log_file = log_dir / 'validate_constraints.log'

        self.log(f"Connected to database: {db_config['database']}")
        self.log(f"Log file: {self.log_file}")

        self.validation_stats = {'validated': 0, 'already_valid': 0, 'failed': 0}

    def log(self, message):
        """Print timestamped message to console and file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] {message}"
        print(log_line)

        # Also write to file
        with open(self.log_file, 'a') as f:
            f.write(log_line + '\n')

    def _original_log(self, message):
        """Print timestamped message (kept for compatibility)"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {message}")

    def log_validation_failure(self, constraint_name, table_name, error_message):
        """Log validation failure to file"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(VALIDATION_LOG, 'a') as f:
            f.write(f"[{timestamp}] {constraint_name} on {table_name}: {error_message}\n")

    def get_invalid_constraints(self):
        """
        Get all foreign key constraints that are NOT VALID

        Returns:
            list: List of (table_name, constraint_name) tuples
        """
        query = """
            SELECT
                tc.table_name,
                tc.constraint_name
            FROM information_schema.table_constraints tc
            JOIN pg_constraint pgc ON tc.constraint_name = pgc.conname
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND pgc.convalidated = false
            ORDER BY tc.table_name, tc.constraint_name
        """

        self.cursor.execute(query)
        return self.cursor.fetchall()

    def validate_constraint(self, table_name, constraint_name):
        """
        Validate a single constraint

        Args:
            table_name: Table name
            constraint_name: Constraint name

        Returns:
            bool: True if validated successfully, False if validation failed
        """
        self.log(f"  Validating {constraint_name} on {table_name}...")

        try:
            start_time = time.time()

            # Validate the constraint
            query = f"ALTER TABLE {table_name} VALIDATE CONSTRAINT {constraint_name}"
            self.cursor.execute(query)
            self.conn.commit()

            elapsed = time.time() - start_time
            self.log(f"    ✅ Validated successfully in {elapsed:.1f}s")
            self.validation_stats['validated'] += 1
            return True

        except psycopg2.errors.ForeignKeyViolation as e:
            # FK validation failed - orphaned records exist
            self.log(f"    ❌ Validation FAILED - orphaned records exist")
            self.log(f"       Error: {str(e)[:200]}")
            self.log_validation_failure(constraint_name, table_name, str(e))
            self.conn.rollback()
            self.validation_stats['failed'] += 1
            return False

        except Exception as e:
            # Other error
            self.log(f"    ❌ Validation error: {e}")
            self.log_validation_failure(constraint_name, table_name, str(e))
            self.conn.rollback()
            self.validation_stats['failed'] += 1
            return False

    def validate_all_constraints(self):
        """Validate all NOT VALID foreign key constraints"""
        self.log("\n" + "="*70)
        self.log("VALIDATING FOREIGN KEY CONSTRAINTS")
        self.log("="*70 + "\n")

        # Get all invalid constraints
        invalid_constraints = self.get_invalid_constraints()

        if not invalid_constraints:
            self.log("ℹ️  No NOT VALID constraints found - all constraints are already valid")
            return True

        self.log(f"Found {len(invalid_constraints)} NOT VALID constraints to validate\n")

        # Validate each constraint
        for table_name, constraint_name in invalid_constraints:
            self.validate_constraint(table_name, constraint_name)

        # Summary
        self.log("\n" + "="*70)
        self.log(f"CONSTRAINT VALIDATION COMPLETE")
        self.log(f"Validated successfully: {self.validation_stats['validated']}")
        self.log(f"Already valid: {self.validation_stats['already_valid']}")
        self.log(f"Failed validation: {self.validation_stats['failed']}")

        if self.validation_stats['failed'] > 0:
            self.log(f"\n⚠️  {self.validation_stats['failed']} constraints failed validation")
            self.log(f"   These constraints have orphaned records that reference non-existent entities")
            self.log(f"   Check {VALIDATION_LOG} for details")
            self.log(f"   Use orphan manifests from analyze_orphans.py for API retrieval")

        self.log("="*70 + "\n")

        return self.validation_stats['failed'] == 0

    def close(self):
        """Close database connection"""
        self.cursor.close()
        self.conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Validate Foreign Key Constraints')
    parser.add_argument('--test', action='store_true', help='Use test database (oadb2_test)')
    args = parser.parse_args()

    validator = ConstraintValidator(test_mode=args.test)

    try:
        success = validator.validate_all_constraints()
        # Don't exit with error if validation failed - just log it
        # The orphaned records are expected and will be retrieved via API
        sys.exit(0)
    except Exception as e:
        validator.log(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        validator.close()

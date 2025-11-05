"""
Phase 4 Orchestrator: Author Profile Building for CF Corpus

Runs all author profiling scripts in sequence:
1. Gender prediction
2. Career stage calculation
3. Complete profile metrics

Requires Phase 5 (query system) to be completed first.
"""

import sys
import os
import subprocess
from datetime import datetime

# Import logging from Phase 5
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '05_db_query'))
from utils import setup_logging
import time


class PipelineStep:
    """Represents a single step in the pipeline"""

    def __init__(self, name, script, description):
        self.name = name
        self.script = script
        self.description = description
        self.start_time = None
        self.end_time = None
        self.success = None
        self.error_message = None

    def run(self, logger):
        """Execute the step"""
        logger.info("\n" + "="*70)
        logger.info(f"STEP: {self.name}")
        logger.info("="*70)
        logger.info(f"Description: {self.description}")
        logger.info(f"Script: {self.script}")
        logger.info("")

        self.start_time = time.time()

        try:
            result = subprocess.run(
                [sys.executable, self.script],
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )

            self.end_time = time.time()

            if result.returncode == 0:
                self.success = True
                logger.info(f"✓ {self.name} completed successfully")
                logger.info(f"  Duration: {self.duration():.1f} seconds")
                return True
            else:
                self.success = False
                self.error_message = result.stderr
                logger.error(f"✗ {self.name} failed with return code {result.returncode}")
                logger.error(f"  Error output:\n{result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            self.end_time = time.time()
            self.success = False
            self.error_message = "Timeout exceeded"
            logger.error(f"✗ {self.name} timed out")
            return False

        except Exception as e:
            self.end_time = time.time()
            self.success = False
            self.error_message = str(e)
            logger.error(f"✗ {self.name} failed with exception: {e}")
            return False

    def duration(self):
        """Get step duration in seconds"""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return 0


def main():
    """Main orchestrator execution"""
    logger = setup_logging('orchestrator_profiles')

    logger.info("="*70)
    logger.info("PHASE 4 ORCHESTRATOR: AUTHOR PROFILE BUILDING")
    logger.info("="*70)
    logger.info("Clinical Flow Cytometry Corpus Author Profiling")
    logger.info(f"Started at: {datetime.now()}")
    logger.info("="*70)

    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Define pipeline steps
    steps = [
        PipelineStep(
            "Gender Prediction",
            os.path.join(script_dir, "python_gender_integration.py"),
            "Predict gender for all CF corpus authors using gender-guesser"
        ),
        PipelineStep(
            "Career Stage Calculation",
            os.path.join(script_dir, "calculate_career_stage.py"),
            "Calculate career stage and publication timeline metrics"
        ),
        PipelineStep(
            "Build Author Profiles",
            os.path.join(script_dir, "build_author_profiles.py"),
            "Calculate authorship patterns, most cited works, and research topics"
        )
    ]

    # Execute pipeline
    pipeline_start = time.time()
    failed_steps = []

    for i, step in enumerate(steps, 1):
        logger.info(f"\n{'#'*70}")
        logger.info(f"# EXECUTING STEP {i}/{len(steps)}")
        logger.info(f"{'#'*70}")

        success = step.run(logger)

        if not success:
            failed_steps.append(step)
            logger.error(f"\nStep {i} failed. Stopping pipeline.")
            break

    pipeline_end = time.time()
    pipeline_duration = pipeline_end - pipeline_start

    # Generate summary report
    logger.info("\n" + "="*70)
    logger.info("PIPELINE EXECUTION SUMMARY")
    logger.info("="*70)
    logger.info(f"Completed at: {datetime.now()}")
    logger.info(f"Total duration: {pipeline_duration/60:.1f} minutes")
    logger.info("")

    # Step-by-step results
    logger.info("Step Results:")
    logger.info("-"*70)
    for i, step in enumerate(steps, 1):
        if step.success is None:
            status = "⊘ NOT RUN"
        elif step.success:
            status = f"✓ SUCCESS ({step.duration()/60:.1f}m)"
        else:
            status = f"✗ FAILED ({step.duration()/60:.1f}m)"

        logger.info(f"{i}. {step.name:.<50} {status}")

    # Overall result
    logger.info("\n" + "="*70)
    if not failed_steps:
        logger.info("✓ PIPELINE COMPLETED SUCCESSFULLY")
        logger.info("="*70)
        logger.info("\nThe CF corpus author profiles are complete!")
        logger.info("\nYou can now begin analysis:")
        logger.info("  - Phase 6: Network building")
        logger.info("  - Phase 10: Gender hypothesis testing")
        logger.info("  - Phase 11: Geography hypothesis testing")
        logger.info("\nProfile includes:")
        logger.info("  ✓ Gender (inferred)")
        logger.info("  ✓ Career stage")
        logger.info("  ✓ Authorship patterns")
        logger.info("  ✓ Citation metrics")
        logger.info("  ✓ Research topics/concepts")
        return 0
    else:
        logger.error("✗ PIPELINE FAILED")
        logger.error("="*70)
        logger.error(f"\nFailed steps: {len(failed_steps)}")
        for step in failed_steps:
            logger.error(f"  - {step.name}: {step.error_message}")
        logger.error("\nPlease review the logs and fix errors before retrying.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

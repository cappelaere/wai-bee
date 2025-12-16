#!/usr/bin/env python3
"""
Example: Process applicants with stop-on-error enabled.

This script demonstrates how to use the stop_on_error parameter to halt
processing immediately when an applicant fails, useful for debugging or
when you want to fix issues before continuing.

Usage:
    python examples/process_with_stop_on_error.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflows.scholarship_workflow import ScholarshipProcessingWorkflow
from utils.config import config
from utils.logging_config import setup_logging, get_logger


def main():
    """Process applicants with stop-on-error enabled."""
    
    # Setup logging
    setup_logging()
    logger = get_logger(__name__)
    
    logger.info("="*60)
    logger.info("Processing with Stop-on-Error Enabled")
    logger.info("="*60)
    
    # Initialize workflow
    workflow = ScholarshipProcessingWorkflow(
        scholarship_folder=config.get_scholarship_folder("Delaney_Wings"),
        outputs_dir=config.OUTPUTS_DIR
    )
    
    # Process applicants with stop_on_error=True
    # This will stop immediately if any applicant fails
    results = workflow.process_all_applicants(
        max_applicants=10,      # Limit to 10 applicants
        skip_stages=[],         # Process all stages
        parallel=True,          # Use parallel processing
        stop_on_error=True      # ✅ Stop immediately on first error
    )
    
    # Display results
    logger.info("\n" + "="*60)
    logger.info("Processing Complete!")
    logger.info("="*60)
    logger.info(f"Total applicants processed: {len(results['applicants'])}")
    logger.info(f"Successful: {results['successful']}")
    logger.info(f"Failed: {results['failed']}")
    
    if results.get('stopped_early'):
        logger.warning(f"\n⚠️  Processing stopped early due to error")
        logger.warning(f"Stopped at applicant: {results['stopped_at']}")
        logger.warning(f"Remaining applicants were not processed")
    else:
        logger.info(f"\n✅ All applicants processed successfully")
    
    logger.info(f"\nTotal duration: {results['total_duration_seconds']:.2f} seconds")
    
    # Show which applicant failed (if any)
    if results['failed'] > 0:
        logger.info("\n" + "="*60)
        logger.info("Failed Applicants:")
        logger.info("="*60)
        for applicant in results['applicants']:
            if not applicant.success:
                logger.error(f"  WAI {applicant.wai_number}: {applicant.error}")


if __name__ == "__main__":
    main()

# Made with Bob

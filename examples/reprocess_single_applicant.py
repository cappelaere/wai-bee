#!/usr/bin/env python3
"""
Reprocess a single applicant to update their JSON with the state field.

This script reprocesses a specific applicant to regenerate their application
JSON file with the newly added state field.

Usage:
    python examples/reprocess_single_applicant.py <wai_number>
    
Example:
    python examples/reprocess_single_applicant.py 82799
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflows.scholarship_workflow import ScholarshipProcessingWorkflow
from utils.config import config
from utils.logging_config import setup_logging, get_logger


def main():
    """Reprocess a single applicant."""
    
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: python examples/reprocess_single_applicant.py <wai_number>")
        print("Example: python examples/reprocess_single_applicant.py 82799")
        sys.exit(1)
    
    wai_number = sys.argv[1]
    
    # Setup logging
    setup_logging()
    logger = get_logger(__name__)
    
    logger.info("="*60)
    logger.info(f"Reprocessing Applicant: {wai_number}")
    logger.info("="*60)
    
    # Initialize workflow
    workflow = ScholarshipProcessingWorkflow(
        scholarship_folder=config.DELANEY_WINGS_FOLDER,
        outputs_dir=config.OUTPUTS_DIR
    )
    
    # Process just the application stage to regenerate JSON
    logger.info(f"\nReprocessing application for WAI {wai_number}...")
    logger.info("This will regenerate the JSON file with the state field.\n")
    
    result = workflow.process_applicant(
        wai_number=wai_number,
        skip_stages=["attachments", "recommendations", "academic", "essays"],  # Only process application
        parallel=False
    )
    
    # Display results
    logger.info("\n" + "="*60)
    logger.info("Reprocessing Complete!")
    logger.info("="*60)
    logger.info(f"Success: {result.success}")
    logger.info(f"Duration: {result.total_duration_seconds:.2f} seconds")
    
    if result.success:
        logger.info(f"\n✅ JSON file updated with state field")
        logger.info(f"Check: outputs/application/Delaney_Wings/{wai_number}/")
    else:
        logger.error(f"\n❌ Failed to reprocess applicant")
        # Check stages for errors
        for stage in result.stages:
            if not stage.success and stage.error:
                logger.error(f"Error in {stage.stage_name}: {stage.error}")


if __name__ == "__main__":
    main()

# Made with Bob

"""
Example script demonstrating workflow usage with different options.

This script shows how to use the ScholarshipProcessingWorkflow
to process applications with various configurations.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflows.scholarship_workflow import ScholarshipProcessingWorkflow
from utils.config import config
from utils.logging_config import setup_logging, get_logger


def main():
    """Run workflow examples."""
    
    # Setup logging
    setup_logging()
    logger = get_logger(__name__)
    
    logger.info("="*60)
    logger.info("Scholarship Processing Workflow Examples")
    logger.info("="*60)
    
    # Initialize workflow
    workflow = ScholarshipProcessingWorkflow(
        scholarship_folder=config.DELANEY_WINGS_FOLDER,
        outputs_dir=config.OUTPUTS_DIR
    )
    
    # Example 1: Process a single applicant
    logger.info("\n" + "="*60)
    logger.info("Example 1: Process Single Applicant")
    logger.info("="*60)
    
    result = workflow.process_applicant(
        wai_number="75179",
        skip_stages=[],  # Process all stages
        parallel=True    # Use parallel processing
    )
    
    logger.info(f"Single applicant result:")
    logger.info(f"  Success: {result.success}")
    logger.info(f"  Stages completed: {len(result.stages)}")
    logger.info(f"  Duration: {result.total_duration_seconds:.2f}s")
    
    # Example 2: Process first 10 applicants
    logger.info("\n" + "="*60)
    logger.info("Example 2: Process First 10 Applicants")
    logger.info("="*60)
    
    results = workflow.process_all_applicants(
        max_applicants=10,  # ✅ Limit to 10 applicants
        skip_stages=[],
        parallel=True
    )
    
    logger.info(f"Batch processing results:")
    logger.info(f"  Total: {results['total_applicants']}")
    logger.info(f"  Successful: {results['successful']}")
    logger.info(f"  Failed: {results['failed']}")
    logger.info(f"  Duration: {results['total_duration_seconds']:.2f}s")
    
    # Example 3: Process specific applicants
    logger.info("\n" + "="*60)
    logger.info("Example 3: Process Specific Applicants")
    logger.info("="*60)
    
    results = workflow.process_all_applicants(
        wai_numbers=["75179", "77747", "82799"],  # ✅ Specific WAI numbers
        skip_stages=[],
        parallel=True
    )
    
    logger.info(f"Specific applicants results:")
    logger.info(f"  Total: {results['total_applicants']}")
    logger.info(f"  Successful: {results['successful']}")
    
    # Example 4: Process all applicants (no limit)
    logger.info("\n" + "="*60)
    logger.info("Example 4: Process All Applicants (Commented Out)")
    logger.info("="*60)
    logger.info("To process all applicants, uncomment the following:")
    logger.info("""
    results = workflow.process_all_applicants(
        max_applicants=None,  # ✅ Process all (or omit parameter)
        skip_stages=[],
        parallel=True
    )
    """)
    
    # Example 5: Skip certain stages
    logger.info("\n" + "="*60)
    logger.info("Example 5: Skip Certain Stages")
    logger.info("="*60)
    
    results = workflow.process_all_applicants(
        max_applicants=3,
        skip_stages=["attachments", "essays"],  # ✅ Skip these stages
        parallel=True
    )
    
    logger.info(f"Partial processing results:")
    logger.info(f"  Skipped stages: {results['skipped_stages']}")
    logger.info(f"  Successful: {results['successful']}")
    
    # Example 6: Sequential processing (no parallel)
    logger.info("\n" + "="*60)
    logger.info("Example 6: Sequential Processing")
    logger.info("="*60)
    
    results = workflow.process_all_applicants(
        max_applicants=2,
        skip_stages=[],
        parallel=False  # ✅ Run stages sequentially
    )
    
    logger.info(f"Sequential processing results:")
    logger.info(f"  Successful: {results['successful']}")
    logger.info(f"  Duration: {results['total_duration_seconds']:.2f}s")
    
    logger.info("\n" + "="*60)
    logger.info("All Examples Complete!")
    logger.info("="*60)


if __name__ == "__main__":
    main()

# Made with Bob

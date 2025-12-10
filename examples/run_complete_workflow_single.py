#!/usr/bin/env python3
"""
Run complete workflow for a single applicant with validation and scoring.

This script processes a single applicant through all workflow stages including:
- Attachment processing with error tracking
- Application extraction with validation and scoring
- Recommendations, academic records, and essays analysis
- Final summary generation

Usage:
    python examples/run_complete_workflow_single.py <wai_number> [scholarship]
    
Examples:
    python examples/run_complete_workflow_single.py 82799
    python examples/run_complete_workflow_single.py 82799 Delaney_Wings
    python examples/run_complete_workflow_single.py 82799 Evans_Wings
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflows.scholarship_workflow import ScholarshipProcessingWorkflow
from utils.config import config
from utils.logging_config import setup_logging, get_logger


def main():
    """Run complete workflow for a single applicant."""
    
    # Check command line arguments
    if len(sys.argv) < 2:
        print("Usage: python examples/run_complete_workflow_single.py <wai_number> [scholarship]")
        print("\nExamples:")
        print("  python examples/run_complete_workflow_single.py 82799")
        print("  python examples/run_complete_workflow_single.py 82799 Delaney_Wings")
        print("  python examples/run_complete_workflow_single.py 82799 Evans_Wings")
        sys.exit(1)
    
    wai_number = sys.argv[1]
    scholarship = sys.argv[2] if len(sys.argv) > 2 else "Delaney_Wings"
    
    # Setup logging
    setup_logging()
    logger = get_logger(__name__)
    
    logger.info("="*70)
    logger.info(f"Complete Workflow for Single Applicant: {wai_number}")
    logger.info(f"Scholarship: {scholarship}")
    logger.info("="*70)
    
    # Determine scholarship folder (parent folder with agents.json)
    if scholarship == "Delaney_Wings":
        scholarship_base = config.DELANEY_WINGS_FOLDER
    elif scholarship == "Evans_Wings":
        scholarship_base = config.EVANS_WINGS_FOLDER
    else:
        logger.error(f"Unknown scholarship: {scholarship}")
        logger.error("Valid options: Delaney_Wings, Evans_Wings")
        sys.exit(1)
    
    # Verify WAI folder exists in Applications subfolder
    wai_folder = scholarship_base / "Applications" / wai_number
    if not wai_folder.exists():
        logger.error(f"WAI folder not found: {wai_folder}")
        logger.info(f"Note: Make sure the WAI folder exists in the Applications directory")
        sys.exit(1)
    
    logger.info(f"\nWAI Folder: {wai_folder}")
    logger.info(f"Scholarship Base: {scholarship_base}")
    logger.info(f"Output Directory: {config.OUTPUTS_DIR}")
    
    # Initialize workflow with base folder (where agents.json is located)
    logger.info("\nInitializing workflow...")
    workflow = ScholarshipProcessingWorkflow(
        scholarship_folder=scholarship_base,
        outputs_dir=config.OUTPUTS_DIR
    )
    
    # Process all stages
    logger.info(f"\nProcessing all stages for WAI {wai_number}...")
    logger.info("Stages: attachments → application → recommendations → academic → essays → summary")
    logger.info("")
    
    result = workflow.process_applicant(
        wai_number=wai_number,
        skip_stages=[],  # Process all stages
        parallel=False  # Sequential processing for clarity
    )
    
    # Display detailed results
    logger.info("\n" + "="*70)
    logger.info("WORKFLOW COMPLETE")
    logger.info("="*70)
    logger.info(f"Overall Success: {result.success}")
    logger.info(f"Total Duration: {result.total_duration_seconds:.2f} seconds")
    logger.info(f"Stages Completed: {len([s for s in result.stages if s.success])}/{len(result.stages)}")
    
    # Show stage-by-stage results
    logger.info("\n" + "-"*70)
    logger.info("Stage Results:")
    logger.info("-"*70)
    
    for stage in result.stages:
        status = "✅ SUCCESS" if stage.success else "❌ FAILED"
        duration = f"{stage.duration_seconds:.2f}s" if stage.duration_seconds else "N/A"
        logger.info(f"{stage.stage_name:20s} {status:12s} Duration: {duration}")
        
        if not stage.success and stage.error:
            logger.error(f"  Error: {stage.error}")
    
    # Show output locations
    if result.success:
        logger.info("\n" + "-"*70)
        logger.info("Output Files:")
        logger.info("-"*70)
        
        scholarship_name = scholarship_base.name
        base_output = Path(config.OUTPUTS_DIR)
        
        outputs = {
            "Attachments": base_output / "attachments" / scholarship_name / wai_number,
            "Application": base_output / "application" / scholarship_name / wai_number,
            "Application Analysis": base_output / "application" / scholarship_name / wai_number / "application_analysis.json",
            "Recommendations": base_output / "recommendations" / scholarship_name / wai_number,
            "Academic": base_output / "academic" / scholarship_name / wai_number,
            "Essays": base_output / "essays" / scholarship_name / wai_number,
            "Summary": base_output / "summary" / scholarship_name / f"{wai_number}_summary.json"
        }
        
        for name, path in outputs.items():
            if path.exists():
                logger.info(f"✓ {name:20s} {path}")
            else:
                logger.warning(f"✗ {name:20s} NOT FOUND: {path}")
        
        # Show validation and scoring info
        logger.info("\n" + "-"*70)
        logger.info("Key Features:")
        logger.info("-"*70)
        logger.info("✓ Application validation with error tracking")
        logger.info("✓ Application scoring (Completeness + Validity + Attachments)")
        logger.info("✓ Attachment processing with file size tracking")
        logger.info("✓ State field extraction for US applicants")
        logger.info("✓ Comprehensive error reporting in JSON outputs")
        
        logger.info("\n" + "="*70)
        logger.info("Review the JSON files to see detailed validation and scoring results!")
        logger.info("="*70)
    else:
        logger.error("\n❌ Workflow failed. Check the logs above for details.")
    
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
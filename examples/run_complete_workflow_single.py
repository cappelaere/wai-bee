#!/usr/bin/env python3
"""
Run complete workflow for a single applicant with extraction, attachments, and scoring.

This script processes a single applicant through the workflow stages including:
- Application extraction (writes application_data.json)
- Attachment processing (writes attachments/*.txt)
- Scoring runner (writes *_analysis.json files)

Usage:
    python examples/run_complete_workflow_single.py <wai_number> [scholarship]
    
Examples:
    python examples/run_complete_workflow_single.py 82799
    python examples/run_complete_workflow_single.py 82799 Delaney_Wings
    python examples/run_complete_workflow_single.py 82799 Evans_Wings
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflows.scholarship_workflow import ScholarshipProcessingWorkflow
from utils.config import config
from utils.logging_config import setup_logging, get_logger


def main():
    """Run complete workflow for a single applicant."""

    parser = argparse.ArgumentParser(
        description="Run workflow for a single applicant (application_extract → attachments → scoring)."
    )
    parser.add_argument("--scholarship", default="Delaney_Wings", help="Scholarship folder name under data/")
    parser.add_argument("--wai", default=None, help="WAI applicant folder name (e.g., 75179)")
    parser.add_argument("--outputs-dir", default=str(config.OUTPUTS_DIR), help="Outputs base directory")
    parser.add_argument("--parallel", action="store_true", help="Run workflow scoring stage in parallel (if supported)")
    parser.add_argument(
        "--skip-stages",
        default="",
        help="Comma-separated list of stages to skip (e.g., attachments,application_extract,scoring)",
    )

    # Backward compatible positional args:
    #   python run_complete_workflow_single.py <wai> [scholarship]
    args, extras = parser.parse_known_args()
    if args.wai is None:
        if len(extras) < 1:
            parser.print_help()
            print("\nPositional usage:")
            print("  python examples/run_complete_workflow_single.py 82799 [Delaney_Wings]")
            return 1
        args.wai = extras[0]
        if len(extras) >= 2:
            args.scholarship = extras[1]

    wai_number = args.wai
    scholarship = args.scholarship
    outputs_dir = Path(args.outputs_dir)
    skip_stages = [s.strip() for s in args.skip_stages.split(",") if s.strip()]
    
    # Setup logging
    setup_logging()
    logger = get_logger(__name__)
    
    logger.info("="*70)
    logger.info(f"Complete Workflow for Single Applicant: {wai_number}")
    logger.info(f"Scholarship: {scholarship}")
    logger.info("="*70)
    
    # Determine scholarship folder (parent folder with agents.json)
    if scholarship in ["Delaney_Wings", "Evans_Wings"]:
        scholarship_base = config.get_scholarship_folder(scholarship)
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
    logger.info(f"Output Directory: {outputs_dir}")
    
    # Initialize workflow with base folder (where agents.json is located)
    logger.info("\nInitializing workflow...")
    workflow = ScholarshipProcessingWorkflow(
        scholarship_folder=scholarship_base,
        outputs_dir=outputs_dir
    )
    
    # Process all stages
    logger.info(f"\nProcessing all stages for WAI {wai_number}...")
    logger.info("Stages: application_extract → attachments → scoring")
    logger.info("")
    
    result = workflow.process_applicant(
        wai_number=wai_number,
        skip_stages=skip_stages,
        parallel=args.parallel
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
        base_output = outputs_dir
        
        outputs = {
            "Attachments": base_output / scholarship_name / wai_number / "attachments",
            "Application Data": base_output / scholarship_name / wai_number / "application_data.json",
            "Application Analysis": base_output / scholarship_name / wai_number / "application_analysis.json",
            "Resume Analysis": base_output / scholarship_name / wai_number / "resume_analysis.json",
            "Essay Analysis": base_output / scholarship_name / wai_number / "essay_analysis.json",
            "Recommendation Analysis": base_output / scholarship_name / wai_number / "recommendation_analysis.json",
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
        logger.info("✓ Schema-driven scoring via ScoringRunner (application/resume/essay/recommendation)")
        logger.info("✓ Attachment processing with file size tracking")
        logger.info("✓ State field extraction for US applicants")
        logger.info("✓ LLM repair loop on schema validation failures")
        
        logger.info("\n" + "="*70)
        logger.info("Review the JSON files to see detailed validation and scoring results!")
        logger.info("="*70)
    else:
        logger.error("\n❌ Workflow failed. Check the logs above for details.")
    
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())

# Made with Bob
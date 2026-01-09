#!/usr/bin/env python3
"""
Process scholarship applicants with configurable options.

This script processes applicants for any configured scholarship,
running all stages in parallel and generating a summary report.
The number of applicants can be customized via command-line arguments.

By default, a preflight check validates all applicant files before processing,
skipping any applicants with missing, empty, or corrupt files.

Usage:
    # Process Delaney Wings with default 20 applicants (preflight enabled by default)
    python examples/process_applicants.py --scholarship Delaney_Wings --max-applicants 20
    
    # Process Evans Wings with default 20 applicants
    python examples/process_applicants.py --scholarship Evans_Wings
    
    # Process without preflight validation
    python examples/process_applicants.py --scholarship Delaney_Wings --no-preflight
    
    # Process all applicants from Delaney Wings
    python examples/process_applicants.py --scholarship Delaney_Wings --max-applicants 1000
"""

import sys
import argparse
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from workflows.scholarship_workflow import ScholarshipProcessingWorkflow
from utils.config import config
from utils.logging_config import setup_logging, get_logger


def main():
    """Process scholarship applicants with full workflow."""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Process scholarship applicants with configurable options",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process Delaney Wings with default 20 applicants
  python examples/process_applicants.py --scholarship Delaney_Wings
  
  # Process Evans Wings with default 20 applicants
  python examples/process_applicants.py --scholarship Evans_Wings
  
  # Process 10 applicants from Evans Wings
  python examples/process_applicants.py --scholarship Evans_Wings --max-applicants 10
  
  # Process all applicants (use large number)
  python examples/process_applicants.py --scholarship Delaney_Wings --max-applicants 1000
        """
    )
    parser.add_argument(
        '--scholarship',
        type=str,
        default='Delaney_Wings',
        help="Scholarship folder name under data/ (default: 'Delaney_Wings')"
    )
    parser.add_argument(
        '--max-applicants',
        type=int,
        default=20,
        help='Maximum number of applicants to process (default: 20)'
    )
    parser.add_argument(
        '--outputs-dir',
        type=Path,
        default=Path("outputs"),
        help="Base outputs directory (default: 'outputs')"
    )
    parser.add_argument(
        '--model',
        type=str,
        default="ollama/llama3.2:3b",
        help="Primary LLM model to use (default: 'ollama/llama3.2:3b')"
    )
    parser.add_argument(
        '--fallback-model',
        type=str,
        default="anthropic/claude-haiku-4-5-20251001",
        help="Fallback LLM model if primary fails (default: 'anthropic/claude-haiku-4-5-20251001')"
    )
    parser.add_argument(
        '--max-retries',
        type=int,
        default=3,
        help="Maximum retry attempts for LLM calls (default: 3)"
    )
    parser.add_argument(
        '--skip-stages',
        type=str,
        default="",
        help="Comma-separated list of stages to skip (e.g., 'attachments,scoring,summary')"
    )
    parser.add_argument(
        '--no-parallel',
        action='store_true',
        help="Disable parallel stage execution for each applicant (default: parallel enabled)"
    )
    parser.add_argument(
        '--stop-on-error',
        action='store_true',
        help="Stop processing when an applicant fails (default: continue)"
    )
    parser.add_argument(
        '--preflight',
        action='store_true',
        default=True,
        help="Run preflight validation before processing (default: enabled)"
    )
    parser.add_argument(
        '--no-preflight',
        action='store_true',
        help="Disable preflight validation (skip file checks, process all applicants)"
    )
    parser.add_argument(
        '--preflight-strict',
        action='store_true',
        help="Abort if any preflight validation errors found (default: skip invalid applicants)"
    )
    
    args = parser.parse_args()
    
    # Get scholarship folder
    scholarship_folder = config.get_scholarship_folder(args.scholarship)
    if not scholarship_folder:
        print(f"Error: Unknown scholarship '{args.scholarship}'")
        print("Available scholarships: Delaney_Wings, Evans_Wings")
        sys.exit(1)
    
    if not scholarship_folder.exists():
        print(f"Error: Scholarship folder does not exist: {scholarship_folder}")
        sys.exit(1)
    
    # Setup logging: console + timestamped file for this workflow run
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"process_{args.scholarship}_{timestamp}.log"
    
    setup_logging(log_file=str(log_file), force=True)
    logger = get_logger(__name__)
    
    logger.info("="*60)
    logger.info(f"Processing {args.max_applicants} Applicants - {args.scholarship}")
    logger.info("="*60)
    logger.info(f"Scholarship folder: {scholarship_folder}")
    logger.info(f"Outputs directory: {args.outputs_dir / args.scholarship}")
    
    # Initialize workflow
    workflow = ScholarshipProcessingWorkflow(
        scholarship_folder=scholarship_folder,
        outputs_dir=args.outputs_dir
    )
    
    skip_stages_list = [s.strip() for s in (args.skip_stages or "").split(",") if s.strip()]

    # Determine preflight setting (--no-preflight overrides --preflight default)
    run_preflight = args.preflight and not args.no_preflight
    
    # Process applicants
    results = workflow.process_all_applicants(
        max_applicants=args.max_applicants,
        skip_stages=skip_stages_list,
        parallel=not args.no_parallel,
        stop_on_error=args.stop_on_error,
        model=args.model,
        fallback_model=args.fallback_model,
        max_retries=args.max_retries,
        preflight=run_preflight,
        preflight_strict=args.preflight_strict,
    )
    
    # Check if aborted due to preflight
    if results.get('aborted'):
        logger.error("\n" + "="*60)
        logger.error("Processing Aborted!")
        logger.error("="*60)
        logger.error(f"Reason: {results.get('abort_reason')}")
        if 'preflight' in results:
            pf = results['preflight']
            logger.error(f"Preflight errors: {pf['errors']}")
            logger.error(f"Preflight warnings: {pf['warnings']}")
            logger.error(f"Invalid applicants: {', '.join(pf['invalid_applicants'])}")
        sys.exit(1)
    
    # Display results
    logger.info("\n" + "="*60)
    logger.info("Processing Complete!")
    logger.info("="*60)
    logger.info(f"Total applicants processed: {results['total_applicants']}")
    logger.info(f"Successful: {results['successful']}")
    logger.info(f"Failed: {results['failed']}")
    logger.info(f"Total duration: {results['total_duration_seconds']:.2f} seconds")
    
    if 'summary' in results:
        summary = results['summary']
        if summary.get('success'):
            logger.info(f"\nSummary files generated:")
            logger.info(f"  CSV: {summary['csv_file']}")
            logger.info(f"  Statistics: {summary['stats_file']}")
            logger.info(f"  Complete applications: {summary['complete_applications']}/{summary['total_applicants']}")
    
    logger.info("\n" + "="*60)
    logger.info(f"Check {args.outputs_dir / args.scholarship} for results")
    logger.info("="*60)


if __name__ == "__main__":
    main()

# Made with Bob

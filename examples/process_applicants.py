#!/usr/bin/env python3
"""
Process scholarship applicants with configurable options.

This script processes applicants for any configured scholarship,
running all stages in parallel and generating a summary report.
The number of applicants can be customized via command-line arguments.

Usage:
    # Process Delaney Wings with default 20 applicants
    python examples/process_applicants.py
    
    # Process Evans Wings with default 20 applicants
    python examples/process_applicants.py Evans_Wings
    
    # Process 10 applicants from Evans Wings
    python examples/process_applicants.py Evans_Wings --max-applicants 10
    
    # Process all applicants from Delaney Wings
    python examples/process_applicants.py Delaney_Wings --max-applicants 1000
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
    """Process scholarship applicants with full workflow."""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Process scholarship applicants with configurable options",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process Delaney Wings with default 20 applicants
  python examples/process_applicants.py
  
  # Process Evans Wings with default 20 applicants
  python examples/process_applicants.py Evans_Wings
  
  # Process 10 applicants from Evans Wings
  python examples/process_applicants.py Evans_Wings --max-applicants 10
  
  # Process all applicants (use large number)
  python examples/process_applicants.py Delaney_Wings --max-applicants 1000
  
Available scholarships:
  - Delaney_Wings (default)
  - Evans_Wings
        """
    )
    parser.add_argument(
        'scholarship',
        nargs='?',
        default='Delaney_Wings',
        choices=['Delaney_Wings', 'Evans_Wings'],
        help='Scholarship to process (default: Delaney_Wings)'
    )
    parser.add_argument(
        '--max-applicants',
        type=int,
        default=20,
        help='Maximum number of applicants to process (default: 20)'
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
    
    # Setup logging
    setup_logging()
    logger = get_logger(__name__)
    
    logger.info("="*60)
    logger.info(f"Processing {args.max_applicants} Applicants - {args.scholarship}")
    logger.info("="*60)
    logger.info(f"Scholarship folder: {scholarship_folder}")
    logger.info(f"Outputs directory: {config.OUTPUTS_DIR}/{args.scholarship}")
    
    # Initialize workflow
    workflow = ScholarshipProcessingWorkflow(
        scholarship_folder=scholarship_folder,
        outputs_dir=config.OUTPUTS_DIR
    )
    
    # Process applicants
    results = workflow.process_all_applicants(
        max_applicants=args.max_applicants,
        skip_stages=[],         # Process all stages
        parallel=True,          # Use parallel processing for speed
        stop_on_error=True      # Continue processing even if an applicant fails
    )
    
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
    logger.info(f"Check outputs/{args.scholarship}/ for results")
    logger.info("="*60)


if __name__ == "__main__":
    main()

# Made with Bob

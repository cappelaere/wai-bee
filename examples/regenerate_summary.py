#!/usr/bin/env python3
"""
Regenerate summary CSV and statistics from existing agent outputs.

This script regenerates the summary CSV and statistics files without
reprocessing any applicants. It reads existing agent outputs and
recalculates scores and statistics.

Usage:
    python examples/regenerate_summary.py
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.summary_agent.agent import SummaryAgent
from utils.config import config
from utils.logging_config import setup_logging, get_logger


def main():
    """Regenerate summary from existing outputs."""
    
    # Setup logging
    setup_logging()
    logger = get_logger(__name__)
    
    logger.info("="*60)
    logger.info("Regenerating Summary from Existing Outputs")
    logger.info("="*60)
    
    # Initialize summary agent
    summary_agent = SummaryAgent(
        outputs_dir=config.OUTPUTS_DIR,
        scholarship_folder=config.get_scholarship_folder("Delaney_Wings")
    )
    
    # Get list of processed applicants from unified output structure
    scholarship_dir = config.OUTPUTS_DIR / "Delaney_Wings"
    if not scholarship_dir.exists():
        logger.error(f"Scholarship outputs directory not found: {scholarship_dir}")
        logger.error("Please run the workflow first to process applicants.")
        sys.exit(1)
    
    wai_numbers = [d.name for d in scholarship_dir.iterdir() if d.is_dir() and not d.name.startswith('.')]
    wai_numbers.sort()
    
    logger.info(f"Found {len(wai_numbers)} processed applicants")
    
    # Generate summary CSV in scholarship folder
    scholarship_dir = config.OUTPUTS_DIR / "Delaney_Wings"
    csv_file = scholarship_dir / "summary.csv"
    stats_file = scholarship_dir / "statistics.txt"
    
    logger.info(f"\nGenerating summary CSV...")
    stats = summary_agent.generate_summary_csv(csv_file, wai_numbers)
    
    # Generate statistics report
    if stats and 'final_score_stats' in stats:
        logger.info(f"Generating statistics report...")
        summary_agent.generate_statistics_report(stats, stats_file)
    else:
        logger.warning("No applicant data available for statistics report")
    
    # Display results
    logger.info("\n" + "="*60)
    logger.info("Summary Regeneration Complete!")
    logger.info("="*60)
    logger.info(f"Total applicants: {stats.get('total_applicants', 0)}")
    logger.info(f"Complete applications: {stats.get('complete_applications', 0)}")
    logger.info(f"\nOutput files:")
    logger.info(f"  CSV: {csv_file}")
    logger.info(f"  Statistics: {stats_file}")
    logger.info("\n" + "="*60)


if __name__ == "__main__":
    main()

# Made with Bob

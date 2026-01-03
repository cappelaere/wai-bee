"""Example script for running the Summary Agent.

This script demonstrates how to use the Summary Agent to aggregate
all agent outputs into a CSV file with statistics.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-06
Version: 1.0.0
License: MIT

Usage:
    python examples/run_summary_agent.py
"""

import logging
import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.summary_agent import SummaryAgent


def setup_logging():
    """Configure logging for the example."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    """Run summary agent example."""
    setup_logging()
    logger = logging.getLogger()
    
    logger.info("="*60)
    logger.info("Summary Agent Example")
    logger.info("="*60)
    
    parser = argparse.ArgumentParser(description="Generate summary CSV/statistics for a scholarship.")
    parser.add_argument("--scholarship", default="Delaney_Wings", help="Scholarship folder name under data/")
    parser.add_argument("--outputs-dir", default="outputs", help="Outputs base directory")
    args = parser.parse_args()

    # Configuration
    outputs_dir = Path(args.outputs_dir)
    scholarship_folder = Path("data") / args.scholarship
    scholarship_name = scholarship_folder.name
    
    # Output files in scholarship folder
    csv_file = Path(f"outputs/{scholarship_name}/summary.csv")
    stats_file = Path(f"outputs/{scholarship_name}/statistics.txt")
    
    logger.info(f"\nScholarship: {scholarship_name}")
    logger.info(f"Outputs directory: {outputs_dir}")
    logger.info(f"CSV output: {csv_file}")
    logger.info(f"Statistics output: {stats_file}")
    
    # Initialize agent
    agent = SummaryAgent(outputs_dir, scholarship_folder)
    
    # Generate summary CSV
    logger.info("\n" + "-"*60)
    logger.info("Generating Summary CSV")
    logger.info("-"*60)
    
    summary_agent = agent  # Keep reference to agent
    stats = summary_agent.generate_summary_csv(
        output_file=csv_file,
        wai_numbers=None  # None = process all
    )
    
    # Display statistics
    logger.info("\n" + "="*60)
    logger.info("STATISTICS SUMMARY")
    logger.info("="*60)
    
    if not stats:
        logger.warning("No statistics available - no application data found")
        return 1
    
    logger.info(f"\nTotal Applicants: {stats['total_applicants']}")
    logger.info(f"Complete Applications: {stats['complete_applications']}")
    logger.info(f"Incomplete Applications: {stats['incomplete_applications']}")
    
    logger.info("\nFinal Score Statistics:")
    fs = stats['final_score_stats']
    logger.info(f"  Min: {fs['min']:.2f}")
    logger.info(f"  Max: {fs['max']:.2f}")
    logger.info(f"  Mean: {fs['mean']:.2f}")
    logger.info(f"  Median (P50): {fs['p50']:.2f}")
    logger.info(f"  P75: {fs['p75']:.2f}")
    logger.info(f"  P90: {fs['p90']:.2f}")
    
    logger.info("\nAgent Score Averages:")
    for agent, agent_stats in stats['agent_score_stats'].items():
        logger.info(f"  {agent.capitalize()}: {agent_stats['mean']:.2f} ({agent_stats['count']} applicants)")
    
    logger.info("\nTop 5 Cities:")
    for i, (city, count) in enumerate(list(stats['top_cities'].items())[:5], 1):
        logger.info(f"  {i}. {city}: {count}")
    
    logger.info("\nTop 5 Countries:")
    for i, (country, count) in enumerate(list(stats['top_countries'].items())[:5], 1):
        logger.info(f"  {i}. {country}: {count}")
    
    # Generate statistics report file
    logger.info("\n" + "-"*60)
    logger.info("Generating Statistics Report")
    logger.info("-"*60)
    
    summary_agent.generate_statistics_report(stats, stats_file)
    
    logger.info("\n" + "="*60)
    logger.info("Summary Generation Complete!")
    logger.info("="*60)
    logger.info(f"CSV file: {csv_file}")
    logger.info(f"Statistics file: {stats_file}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

# Made with Bob

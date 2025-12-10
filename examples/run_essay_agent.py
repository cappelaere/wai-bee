"""Example script for running the Essay Agent.

This script demonstrates how to use the Essay Agent to analyze
personal essays from scholarship applications.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-06
Version: 1.0.0
License: MIT

Usage:
    python examples/run_essay_agent.py
"""

import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.essay_agent import EssayAgent


def setup_logging():
    """Configure logging for the example."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    """Run essay analysis example."""
    setup_logging()
    logger = logging.getLogger()
    
    logger.info("="*60)
    logger.info("Essay Agent Example")
    logger.info("="*60)
    
    # Configuration
    attachments_dir = Path("outputs/attachments")
    scholarship_name = "Delaney_Wings"
    criteria_path = Path("data/Delaney_Wings/criteria/essay_criteria.txt")
    output_dir = Path("outputs/essays")
    
    # Test with a single WAI application
    wai_number = "77747"
    
    logger.info(f"\nAnalyzing essays for WAI {wai_number}")
    logger.info(f"Attachments directory: {attachments_dir}")
    logger.info(f"Scholarship: {scholarship_name}")
    logger.info(f"Criteria: {criteria_path}")
    logger.info(f"Output directory: {output_dir}")
    
    # Initialize agent
    agent = EssayAgent()
    
    # Analyze single application
    result = agent.analyze_essays(
        attachments_dir=attachments_dir,
        scholarship_name=scholarship_name,
        wai_number=wai_number,
        criteria_path=criteria_path,
        model="ollama/llama3.2:3b",
        fallback_model="ollama/llama3:latest",
        max_retries=3,
        output_dir=output_dir
    )
    
    if result:
        logger.info("\n" + "="*60)
        logger.info("Analysis Results")
        logger.info("="*60)
        logger.info(f"WAI Number: {result.wai_number}")
        logger.info(f"Summary: {result.summary}")
        logger.info(f"\nScores:")
        logger.info(f"  Motivation: {result.scores.motivation_score}")
        logger.info(f"  Goals Clarity: {result.scores.goals_clarity_score}")
        logger.info(f"  Character/Service/Leadership: {result.scores.character_service_leadership_score}")
        logger.info(f"  Overall: {result.scores.overall_score}")
        logger.info(f"\nSource Files: {', '.join(result.source_files)}")
        logger.info(f"Model Used: {result.model_used}")
    else:
        logger.error("Essay analysis failed")
        return 1
    
    # Optional: Process multiple applications in batch
    logger.info("\n" + "="*60)
    logger.info("Batch Processing Example")
    logger.info("="*60)
    
    # Process first 5 WAI applications
    stats = agent.process_batch(
        attachments_dir=attachments_dir,
        scholarship_name=scholarship_name,
        criteria_path=criteria_path,
        output_dir=output_dir,
        model="ollama/llama3.2:3b",
        fallback_model="ollama/llama3:latest",
        max_retries=3,
        wai_numbers=None  # None = process all
    )
    
    logger.info("\n" + "="*60)
    logger.info("Batch Processing Results")
    logger.info("="*60)
    logger.info(f"Total: {stats['total']}")
    logger.info(f"Successful: {stats['successful']}")
    logger.info(f"Failed: {stats['failed']}")
    logger.info(f"Skipped: {stats['skipped']}")
    logger.info(f"Duration: {stats['duration']:.2f}s")
    logger.info(f"Average per WAI: {stats['average_per_wai']:.2f}s")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

# Made with Bob

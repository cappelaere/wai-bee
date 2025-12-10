"""Example script for calculating final weighted scores.

This script demonstrates how to use the score calculator to compute
final weighted scores from multiple agent outputs.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-06
Version: 1.0.0
License: MIT

Usage:
    python examples/calculate_final_scores.py
"""

import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.score_calculator import (
    load_weights,
    calculate_wai_final_score,
    load_agent_scores
)


def setup_logging():
    """Configure logging for the example."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    """Calculate final scores for sample applications."""
    setup_logging()
    logger = logging.getLogger()
    
    logger.info("="*60)
    logger.info("Final Score Calculator Example")
    logger.info("="*60)
    
    # Configuration
    scholarship_folder = Path("data/Delaney_Wings")
    outputs_dir = Path("outputs")
    scholarship_name = "Delaney_Wings"
    
    # Test with WAI 77747
    wai_number = "77747"
    
    logger.info(f"\nCalculating final score for WAI {wai_number}")
    logger.info(f"Scholarship: {scholarship_name}")
    
    # Load weights
    logger.info("\n" + "-"*60)
    logger.info("Loading Weights Configuration")
    logger.info("-"*60)
    weights = load_weights(scholarship_folder)
    logger.info(f"Scholarship: {weights['scholarship_name']}")
    logger.info(f"Description: {weights['description']}")
    logger.info("\nWeights:")
    for agent, config in weights['weights'].items():
        logger.info(f"  {agent}: {config['weight']:.2f} - {config['description']}")
    
    # Load agent scores
    logger.info("\n" + "-"*60)
    logger.info("Loading Agent Scores")
    logger.info("-"*60)
    scores = load_agent_scores(outputs_dir, scholarship_name, wai_number)
    for agent, score in scores.items():
        if score is not None:
            logger.info(f"  {agent}: {score}")
        else:
            logger.info(f"  {agent}: Not available")
    
    # Calculate final score
    logger.info("\n" + "-"*60)
    logger.info("Calculating Final Score")
    logger.info("-"*60)
    result = calculate_wai_final_score(
        scholarship_folder,
        outputs_dir,
        scholarship_name,
        wai_number
    )
    
    # Display results
    logger.info("\n" + "="*60)
    logger.info("FINAL SCORE RESULTS")
    logger.info("="*60)
    logger.info(f"WAI Number: {result['wai_number']}")
    logger.info(f"Scholarship: {result['scholarship_name']}")
    logger.info(f"\nFinal Score: {result['final_score']:.2f} / 100")
    logger.info(f"Complete: {'Yes' if result['complete'] else 'No'}")
    
    if result['missing_agents']:
        logger.warning(f"Missing agents: {', '.join(result['missing_agents'])}")
    
    logger.info("\nScore Breakdown:")
    for agent, details in result['breakdown'].items():
        logger.info(f"  {agent}:")
        logger.info(f"    Score: {details['score']}")
        logger.info(f"    Weight: {details['weight']:.2f}")
        logger.info(f"    Contribution: {details['contribution']:.2f}")
    
    # Calculate for multiple applications
    logger.info("\n" + "="*60)
    logger.info("Batch Score Calculation")
    logger.info("="*60)
    
    # Get list of WAI folders with essay analysis
    essay_dir = outputs_dir / "essays" / scholarship_name
    if essay_dir.exists():
        wai_folders = [d for d in essay_dir.iterdir() if d.is_dir()]
        logger.info(f"Found {len(wai_folders)} WAI folders with essay analysis")
        
        results = []
        for wai_dir in wai_folders[:5]:  # Process first 5
            wai_num = wai_dir.name
            try:
                result = calculate_wai_final_score(
                    scholarship_folder,
                    outputs_dir,
                    scholarship_name,
                    wai_num
                )
                results.append(result)
                logger.info(f"  WAI {wai_num}: {result['final_score']:.2f}")
            except Exception as e:
                logger.error(f"  WAI {wai_num}: Error - {e}")
        
        # Sort by final score
        results.sort(key=lambda x: x['final_score'], reverse=True)
        
        logger.info("\n" + "-"*60)
        logger.info("Top Ranked Applications")
        logger.info("-"*60)
        for i, result in enumerate(results[:5], 1):
            complete_marker = "✓" if result['complete'] else "⚠"
            logger.info(f"{i}. WAI {result['wai_number']}: {result['final_score']:.2f} {complete_marker}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

# Made with Bob

#!/usr/bin/env python3
"""
Test application scoring functionality.

This script tests the new application scoring feature by processing
a single applicant and verifying that both extraction and scoring work.

Usage:
    python examples/test_application_scoring.py [wai_number]
    
Example:
    python examples/test_application_scoring.py 101127
"""

import sys
import json
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.application_agent.agent import ApplicationAgent
from utils.config import config
from utils.logging_config import setup_logging, get_logger


def main():
    """Test application scoring on a single applicant."""
    
    # Get WAI number from command line or use default
    wai_number = sys.argv[1] if len(sys.argv) > 1 else "101127"
    
    # Setup logging
    setup_logging()
    logger = get_logger(__name__)
    
    logger.info("="*60)
    logger.info(f"Testing Application Scoring: WAI {wai_number}")
    logger.info("="*60)
    
    # Initialize application agent
    agent = ApplicationAgent()
    
    # Process the application
    logger.info(f"\nProcessing application for WAI {wai_number}...")
    result = agent.analyze_application(
        wai_number=wai_number,
        scholarship_folder=str(config.get_scholarship_folder("Delaney_Wings")),
        output_dir=str(config.OUTPUTS_DIR),
        model="ollama/llama3.2:3b",  # Use 3b model for scoring
        max_retries=3
    )
    
    if not result:
        logger.error(f"❌ Failed to process application for WAI {wai_number}")
        sys.exit(1)
    
    # Check extraction results
    logger.info("\n" + "="*60)
    logger.info("Extraction Results:")
    logger.info("="*60)
    logger.info(f"Name: {result.name}")
    logger.info(f"City: {result.city}")
    logger.info(f"State: {result.state or 'N/A'}")
    logger.info(f"Country: {result.country}")
    
    # Check if analysis file was created
    analysis_path = config.OUTPUTS_DIR / "application" / "Delaney_Wings" / wai_number / "application_analysis.json"
    
    if analysis_path.exists():
        logger.info("\n" + "="*60)
        logger.info("Scoring Results:")
        logger.info("="*60)
        
        with open(analysis_path, 'r') as f:
            analysis = json.load(f)
        
        scores = analysis.get('scores', {})
        logger.info(f"Completeness Score: {scores.get('completeness_score', 0)}/30")
        logger.info(f"Validity Score: {scores.get('validity_score', 0)}/30")
        logger.info(f"Attachment Score: {scores.get('attachment_score', 0)}/40")
        logger.info(f"Overall Score: {scores.get('overall_score', 0)}/100")
        
        logger.info(f"\nSummary: {analysis.get('summary', 'N/A')}")
        
        if analysis.get('completeness_issues'):
            logger.info(f"\nCompleteness Issues:")
            for issue in analysis['completeness_issues']:
                logger.info(f"  - {issue}")
        
        if analysis.get('validity_issues'):
            logger.info(f"\nValidity Issues:")
            for issue in analysis['validity_issues']:
                logger.info(f"  - {issue}")
        
        logger.info(f"\nAttachment Status: {analysis.get('attachment_status', 'N/A')}")
        
        logger.info("\n" + "="*60)
        logger.info("✅ Application Scoring Test PASSED")
        logger.info("="*60)
        logger.info(f"Files created:")
        logger.info(f"  - Extraction: outputs/application/Delaney_Wings/{wai_number}/{wai_number}_*_application.json")
        logger.info(f"  - Analysis: {analysis_path}")
        
    else:
        logger.warning("\n" + "="*60)
        logger.warning("⚠️  Analysis file not created")
        logger.warning("="*60)
        logger.warning("Extraction succeeded but scoring may have failed")
        logger.warning(f"Expected file: {analysis_path}")


if __name__ == "__main__":
    main()

# Made with Bob

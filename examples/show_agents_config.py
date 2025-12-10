"""Example script for displaying agents configuration.

This script demonstrates how to load and display agent configurations
from scholarship folders.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-06
Version: 1.0.0
License: MIT

Usage:
    python examples/show_agents_config.py
"""

import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.agents_config import (
    load_agents_config,
    get_agent_config,
    get_enabled_agents,
    get_scoring_agents,
    validate_agents_config,
    print_agents_summary
)


def setup_logging():
    """Configure logging for the example."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    """Display agents configuration."""
    setup_logging()
    logger = logging.getLogger()
    
    logger.info("="*60)
    logger.info("Agents Configuration Viewer")
    logger.info("="*60)
    
    # Load Delaney Wings configuration
    scholarship_folder = Path("data/Delaney_Wings")
    
    logger.info(f"\nScholarship: {scholarship_folder.name}")
    
    # Validate configuration
    logger.info("\n" + "-"*60)
    logger.info("Validating Configuration")
    logger.info("-"*60)
    is_valid, errors = validate_agents_config(scholarship_folder)
    if is_valid:
        logger.info("✓ Configuration is valid")
    else:
        logger.error("✗ Configuration has errors:")
        for error in errors:
            logger.error(f"  - {error}")
        return 1
    
    # Print summary
    logger.info("\n" + "-"*60)
    logger.info("Configuration Summary")
    logger.info("-"*60)
    print_agents_summary(scholarship_folder)
    
    # Show detailed agent information
    logger.info("\n" + "="*60)
    logger.info("Detailed Agent Information")
    logger.info("="*60)
    
    config = load_agents_config(scholarship_folder)
    
    for agent in config['agents']:
        logger.info(f"\n{agent['display_name']}")
        logger.info("-" * len(agent['display_name']))
        logger.info(f"Name: {agent['name']}")
        logger.info(f"Description: {agent['description']}")
        logger.info(f"Enabled: {'Yes' if agent.get('enabled', True) else 'No'}")
        logger.info(f"Required: {'Yes' if agent.get('required', False) else 'No'}")
        
        if agent.get('weight') is not None:
            logger.info(f"Weight: {agent['weight']:.2f} ({agent['weight']*100:.0f}%)")
        else:
            logger.info("Weight: N/A (non-scoring agent)")
        
        logger.info(f"Output Directory: {agent['output_directory']}")
        logger.info(f"Output File: {agent['output_file']}")
        
        if agent.get('schema'):
            logger.info(f"Schema: {agent['schema']}")
        
        if agent.get('criteria'):
            logger.info(f"Criteria: {agent['criteria']}")
        
        logger.info("Input Files:")
        for input_file in agent['input_files']:
            logger.info(f"  - {input_file}")
        
        logger.info("Evaluates:")
        for item in agent['evaluates']:
            logger.info(f"  - {item}")
    
    # Show scoring breakdown
    logger.info("\n" + "="*60)
    logger.info("Scoring Breakdown")
    logger.info("="*60)
    
    scoring_agents = get_scoring_agents(scholarship_folder)
    total_weight = sum(agent.get('weight', 0) for agent in scoring_agents)
    
    logger.info(f"\nTotal Weight: {total_weight:.2f}")
    logger.info("\nAgent Contributions:")
    for agent in scoring_agents:
        weight = agent.get('weight', 0)
        percentage = weight * 100
        logger.info(f"  {agent['display_name']}: {weight:.2f} ({percentage:.0f}%)")
    
    logger.info("\nFinal Score Calculation:")
    logger.info("  final_score = sum(agent_score * weight) for all scoring agents")
    logger.info("\nExample:")
    logger.info("  Application: 85 * 0.20 = 17.0")
    logger.info("  Recommendation: 90 * 0.25 = 22.5")
    logger.info("  Academic: 88 * 0.25 = 22.0")
    logger.info("  Essay: 92 * 0.30 = 27.6")
    logger.info("  Final Score: 89.1 / 100")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

# Made with Bob

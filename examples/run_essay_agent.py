"""Example script for running essay scoring via ScoringRunner.

This script demonstrates how to use the generic ScoringRunner to score
the essay artifact and persist `outputs/<scholarship>/<wai>/essay_analysis.json`.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-06
Version: 1.0.0
License: MIT

Usage:
    python examples/run_essay_agent.py
"""

import logging
import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.scoring_runner import ScoringRunner


def setup_logging():
    """Configure logging for the example."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def main():
    """Run essay scoring example."""
    setup_logging()
    logger = logging.getLogger()
    
    logger.info("="*60)
    logger.info("Essay Scoring Example (ScoringRunner)")
    logger.info("="*60)
    
    parser = argparse.ArgumentParser(description="Run essay scoring for a single applicant.")
    parser.add_argument("--scholarship", default="Delaney_Wings", help="Scholarship folder name under data/")
    parser.add_argument("--wai", default="75179", help="WAI applicant folder name (e.g., 75179)")
    parser.add_argument("--outputs-dir", default="outputs", help="Outputs base directory")
    parser.add_argument("--model", default="ollama/llama3.2:3b", help="Primary LLM model")
    parser.add_argument("--fallback-model", default="ollama/llama3:latest", help="Fallback LLM model")
    parser.add_argument("--max-retries", type=int, default=3, help="Max scoring retries")
    args = parser.parse_args()

    scholarship_folder = Path("data") / args.scholarship
    outputs_dir = Path(args.outputs_dir)
    model = args.model
    fallback_model = args.fallback_model
    max_retries = args.max_retries
    wai_number = args.wai
    
    logger.info(f"\nAnalyzing essays for WAI {wai_number}")
    logger.info(f"Scholarship: {scholarship_folder.name}")
    logger.info(f"Outputs directory: {outputs_dir}")

    # Initialize runner
    runner = ScoringRunner(scholarship_folder, outputs_dir)

    # Score a single applicant's essay artifact
    res = runner.run_agent_for_wai(
        wai_number=wai_number,
        agent="essay",
        model=model,
        fallback_model=fallback_model,
        max_retries=max_retries,
    )

    if res.success:
        logger.info(f"✓ Essay scoring complete: {res.output_path}")
        return 0

    logger.error(f"✗ Essay scoring failed: {res.error}")
    return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

# Made with Bob

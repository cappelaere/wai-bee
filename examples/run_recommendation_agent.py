"""Example script for running recommendation scoring via ScoringRunner.

This script demonstrates how to use the generic ScoringRunner to score the
recommendation artifact and persist `outputs/<scholarship>/<wai>/recommendation_analysis.json`.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-05
Version: 1.0.0
License: MIT
"""

import logging
import sys
import argparse
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.scoring_runner import ScoringRunner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger()


def main():
    """Run the recommendation scoring example."""
    
    print("\n" + "="*60)
    print("Recommendation Scoring Example (ScoringRunner)")
    print("="*60)
    print("\nThis agent analyzes recommendation letters using LLM and")
    print("generates structured evaluation reports with scores.")
    print("\nNote: This agent uses Ollama for local LLM inference.")
    print("Make sure Ollama is installed and running.")
    print("Install from: https://ollama.ai")
    print("Pull models with:")
    print("  ollama pull llama3.2:3b")
    print("  ollama pull llama3:latest  # Fallback model")
    print("\n" + "="*60)
    
    parser = argparse.ArgumentParser(description="Run recommendation scoring for a single applicant.")
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
    
    # Initialize runner
    print("\nInitializing ScoringRunner...")
    runner = ScoringRunner(scholarship_folder, outputs_dir)

    wai_number = args.wai

    print(f"\nScoring recommendations for WAI: {wai_number}")
    print("="*60)
    
    res = runner.run_agent_for_wai(
        wai_number=wai_number,
        agent="recommendation",
        model=model,
        fallback_model=fallback_model,
        max_retries=max_retries,
    )
    
    if res.success:
        print(f"✓ Wrote: {res.output_path}")
        print("\nDone! Check: outputs/Delaney_Wings/<wai>/recommendation_analysis.json")
        print()
        return

    print(f"✗ Scoring failed: {res.error}")
    print()


if __name__ == "__main__":
    main()

# Made with Bob
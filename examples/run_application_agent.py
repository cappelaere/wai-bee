"""Example script for running application extraction.

This script demonstrates how to use the ApplicationAgent to extract applicant
fields from the main application PDF and write `application_data.json`.

Note: Scoring is now handled by `agents.scoring_runner.ScoringRunner`.
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.application_agent import ApplicationAgent


def main():
    """Run the Application Agent (extraction only)."""
      
    parser = argparse.ArgumentParser(description="Run application extraction for a single applicant.")
    parser.add_argument("--scholarship", default="Delaney_Wings", help="Scholarship folder name under data/")
    parser.add_argument("--wai", default="75179", help="WAI applicant folder name (e.g., 75179)")
    parser.add_argument("--outputs-dir", default="outputs", help="Outputs base directory")
    parser.add_argument("--model", default="ollama/llama3.2:3b", help="Primary LLM model")
    parser.add_argument("--fallback-model", default="ollama/llama3:latest", help="Fallback LLM model")
    parser.add_argument("--max-retries", type=int, default=3, help="Max extraction retries")
    args = parser.parse_args()

    scholarship_folder = Path("data") / args.scholarship
    wai_number = args.wai
    outputs_dir = args.outputs_dir

    print("Initializing Application Agent...")
    agent = ApplicationAgent(scholarship_folder)

    print(f"\nExtracting application for: {scholarship_folder.name} / {wai_number}")
    print("=" * 60)

    result = agent.analyze_application(
        wai_number=wai_number,
        output_dir=outputs_dir,
        model=args.model,
        fallback_model=args.fallback_model,
        max_retries=args.max_retries,
    )
    # Print summary
    print("\n" + "=" * 60)
    print("EXTRACTION SUMMARY")
    print("=" * 60)
   
    print(f"result: {result}")


if __name__ == "__main__":
    main()

# Made with Bob

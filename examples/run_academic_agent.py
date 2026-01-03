"""Example script for running resume scoring via ScoringRunner.

This script demonstrates how to use the generic ScoringRunner to score
the resume artifact (named `resume` in agents.json), which is persisted to
`outputs/<scholarship>/<wai>/resume_analysis.json`.

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
    """Run the resume scoring example."""
    
    print("\n" + "="*60)
    print("Resume Scoring Example (ScoringRunner)")
    print("="*60)
    print("\nThis runner scores the resume/CV artifact using the generated prompts/schemas")
    print("and writes a schema-validated JSON output per applicant.")
    print("\nNote: This agent uses Ollama for local LLM inference.")
    print("Make sure Ollama is installed and running.")
    print("Install from: https://ollama.ai")
    print("Pull models with:")
    print("  ollama pull llama3.2:3b")
    print("  ollama pull llama3:latest  # Fallback model")
    print("\n" + "="*60)
    
    parser = argparse.ArgumentParser(description="Run resume scoring for multiple applicants.")
    parser.add_argument("--scholarship", default="Delaney_Wings", help="Scholarship folder name under data/")
    parser.add_argument("--outputs-dir", default="outputs", help="Outputs base directory")
    parser.add_argument("--model", default="ollama/llama3.2:3b", help="Primary LLM model")
    parser.add_argument("--fallback-model", default="ollama/llama3:latest", help="Fallback LLM model")
    parser.add_argument("--max-retries", type=int, default=3, help="Max scoring retries per applicant")
    parser.add_argument("--max-wai-folders", type=int, default=10, help="Process first N applicants")
    args = parser.parse_args()

    # Initialize runner
    print("\nInitializing ScoringRunner...")
    scholarship_folder = Path("data") / args.scholarship
    outputs_dir = Path(args.outputs_dir)
    runner = ScoringRunner(scholarship_folder, outputs_dir)

    model = args.model
    fallback_model = args.fallback_model
    max_wai_folders = args.max_wai_folders
    max_retries = args.max_retries
    
    print(f"\nScoring resumes for: {scholarship_folder.name}")
    print("="*60)

    wai_numbers = sorted(
        [p.name for p in (scholarship_folder / "Applications").iterdir() if p.is_dir()]
    )[:max_wai_folders]
    if not wai_numbers:
        print("No applicants found under data/Delaney_Wings/Applications/")
        return

    success = 0
    failed = 0
    for wai in wai_numbers:
        res = runner.run_agent_for_wai(
            wai_number=wai,
            agent="resume",
            model=model,
            fallback_model=fallback_model,
            max_retries=max_retries,
        )
        if res.success:
            success += 1
            print(f"✓ {wai}: wrote {res.output_path}")
        else:
            failed += 1
            print(f"✗ {wai}: {res.error}")

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"Total: {len(wai_numbers)}")
    print(f"Successful: {success}")
    print(f"Failed: {failed}")
    print("\nOutputs are under: outputs/Delaney_Wings/<wai>/resume_analysis.json")
    print()


if __name__ == "__main__":
    main()

# Made with Bob

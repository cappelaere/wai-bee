"""Run a single scoring artifact for one WAI applicant.

This script is a lightweight testing harness:
- Ensure application extraction exists (application_data.json)
- Ensure attachments exist (outputs/<scholarship>/<wai>/attachments/*.txt)
- Run ScoringRunner for one scoring artifact (default: recommendation)

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

from agents.application_agent import ApplicationAgent
from agents.attachment_agent import AttachmentAgent
from agents.scoring_runner import ScoringRunner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger()


def main():
    """Run a single scoring artifact for one applicant."""
    
    print("\n" + "="*60)
    print("Single Applicant - Single Artifact Scoring")
    print("="*60)
    
    parser = argparse.ArgumentParser(description="Run a single scoring artifact for one applicant.")
    parser.add_argument("--scholarship", default="Delaney_Wings", help="Scholarship folder name under data/")
    parser.add_argument("--wai", default="75179", help="WAI applicant folder name (e.g., 75179)")
    parser.add_argument(
        "--agent",
        default="recommendation",
        choices=["application", "resume", "essay", "recommendation"],
        help="Which scoring artifact to run",
    )
    parser.add_argument("--outputs-dir", default="outputs", help="Outputs base directory")
    parser.add_argument("--model", default="ollama/llama3.2:3b", help="Primary LLM model")
    parser.add_argument("--fallback-model", default="ollama/llama3:latest", help="Fallback LLM model")
    parser.add_argument("--max-retries", type=int, default=3, help="Max scoring retries")
    args = parser.parse_args()

    wai_number = args.wai
    scholarship_folder = Path("data") / args.scholarship
    outputs_dir = Path(args.outputs_dir)
    agent_name = args.agent
    model = args.model
    fallback_model = args.fallback_model
    max_retries = args.max_retries
    
    print(f"\nProcessing WAI: {wai_number}")
    print(f"Scholarship folder: {scholarship_folder}")
    print(f"Model: {model}")
    print("="*60)

    # Ensure extraction exists
    app_data_path = outputs_dir / scholarship_folder.name / wai_number / "application_data.json"
    if not app_data_path.exists():
        print("\nRunning application extraction first...")
        ApplicationAgent(scholarship_folder).analyze_application(
            wai_number=wai_number,
            output_dir=str(outputs_dir),
            model=model,
            fallback_model=fallback_model,
            max_retries=max_retries,
        )

    # Ensure attachments exist
    attachments_dir = outputs_dir / scholarship_folder.name / wai_number / "attachments"
    if not attachments_dir.exists():
        print("\nRunning attachment processing first...")
        AttachmentAgent().process_single_wai(
            wai_number=wai_number,
            scholarship_folder=str(scholarship_folder),
            output_dir=str(outputs_dir),
            model=model,
            fallback_model=fallback_model,
        )

    runner = ScoringRunner(scholarship_folder, outputs_dir)
    res = runner.run_agent_for_wai(
        wai_number=wai_number,
        agent=agent_name,
        model=model,
        fallback_model=fallback_model,
        max_retries=max_retries,
    )

    print("\n" + "="*60)
    print("COMPLETE")
    print("="*60)
    if res.success:
        print(f"✓ {agent_name} scoring wrote: {res.output_path}")
    else:
        print(f"✗ {agent_name} scoring failed: {res.error}")
    print()


if __name__ == "__main__":
    main()

# Made with Bob

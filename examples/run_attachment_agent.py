"""
Example script for running the Attachment Agent.

This script demonstrates how to use the Attachment Agent to process
scholarship application attachments, remove PII, and save redacted text files.
"""

import sys
import argparse
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.attachment_agent import AttachmentAgent


def main():
    """Run the Attachment Agent on scholarship application attachments."""
    
    # Check if Ollama is available
    print("Note: This agent uses Ollama for local LLM inference.")
    print("Make sure Ollama is installed and running.")
    print("Install from: https://ollama.ai")
    print("Pull models with:")
    print("  ollama pull llama3.2:1b")
    print("  ollama pull llama3:latest  # Optional fallback model\n")
    
    parser = argparse.ArgumentParser(description="Run attachment preprocessing for a scholarship.")
    parser.add_argument("--scholarship", default="Delaney_Wings", help="Scholarship folder name under data/")
    parser.add_argument("--outputs-dir", default="outputs", help="Outputs base directory")
    parser.add_argument("--model", default="ollama/llama3.2:1b", help="Primary LLM model for PII removal")
    parser.add_argument("--fallback-model", default="ollama/llama3:latest", help="Fallback LLM model")
    parser.add_argument("--max-wai-folders", type=int, default=5, help="Process first N WAI folders")
    parser.add_argument("--max-files-per-folder", type=int, default=5, help="Max attachments per WAI")
    parser.add_argument("--skip-processed", action="store_true", help="Skip WAI folders already processed")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite existing outputs")
    args = parser.parse_args()

    # Initialize the agent
    print("Initializing Attachment Agent...")
    agent = AttachmentAgent()

    scholarship_base = Path("data") / args.scholarship
    applications_dir = scholarship_base / "Applications"
    
    # Process attachments
    print(f"\nProcessing attachments from: {applications_dir}")
    print("=" * 60)
    
    result = agent.process_attachments(
        scholarship_folder=str(applications_dir),
        max_wai_folders=args.max_wai_folders,
        max_files_per_folder=args.max_files_per_folder,
        skip_processed=args.skip_processed,
        overwrite=args.overwrite,
        model=args.model,
        fallback_model=args.fallback_model,
        output_dir=args.outputs_dir,
    )
    
    # Print summary
    print("\n" + "=" * 60)
    print("PROCESSING SUMMARY")
    print("=" * 60)
    print(f"Total attachments: {result.total}")
    print(f"Successfully processed: {result.successful}")
    print(f"Failed: {result.failed}")
    
    # Print timing information
    if result.total_duration:
        print(f"\nTiming Information:")
        print(f"  Total duration: {result.total_duration:.2f} seconds")
        if result.avg_duration_per_file:
            print(f"  Average per file: {result.avg_duration_per_file:.2f} seconds")
    
    if result.errors:
        print(f"\nErrors encountered:")
        for error in result.errors:
            print(f"  - WAI {error.wai_number}: {error.error_message}")
            if error.source_file:
                print(f"    File: {error.source_file}")
    
    print("\nDone! Check the outputs folder for generated .txt files.")
    print(f"Example: {args.outputs_dir}/{args.scholarship}/<wai>/attachments/<file>.txt")
    print("\nEach WAI folder also contains a _processing_summary.json file with statistics.")


if __name__ == "__main__":
    main()

# Made with Bob

"""
Example script for running the Attachment Agent.

This script demonstrates how to use the Attachment Agent to process
scholarship application attachments, remove PII, and save redacted text files.
"""

import sys
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
    
    # Initialize the agent
    print("Initializing Attachment Agent...")
    agent = AttachmentAgent()
    
    # Define the scholarship folder path
    scholarship_folder = "data/Delaney_Wings/Applications"
    
    # Process attachments
    print(f"\nProcessing attachments from: {scholarship_folder}")
    print("=" * 60)
    
    result = agent.process_attachments(
        scholarship_folder=scholarship_folder,
        max_wai_folders=5,         # Process first 5 WAI folders (remove or set to None for all)
        max_files_per_folder=5,    # Process first 5 attachments per folder
        skip_processed=True,       # Skip attachments that already have .txt output
        overwrite=False,           # Don't overwrite existing .txt files
        model="ollama/llama3.2:1b",  # Primary model for PII removal
        fallback_model="ollama/llama3:latest"  # Fallback model if primary fails (optional)
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
    print("Example: outputs/attachments/Delaney_Wings/75179/75179_19_1.txt")
    print("\nEach WAI folder also contains a _processing_summary.txt file with statistics.")


if __name__ == "__main__":
    main()

# Made with Bob

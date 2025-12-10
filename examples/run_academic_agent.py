"""Example script for running the Academic Agent.

This script demonstrates how to use the AcademicAgent to analyze
resume/CV files from scholarship applications.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-05
Version: 1.0.0
License: MIT
"""

import logging
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.academic_agent import AcademicAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger()


def main():
    """Run the Academic Agent example."""
    
    print("\n" + "="*60)
    print("Academic Agent Example")
    print("="*60)
    print("\nThis agent analyzes resume/CV files using LLM and")
    print("generates structured academic profile evaluations with scores.")
    print("\nNote: This agent uses Ollama for local LLM inference.")
    print("Make sure Ollama is installed and running.")
    print("Install from: https://ollama.ai")
    print("Pull models with:")
    print("  ollama pull llama3.2:3b")
    print("  ollama pull llama3:latest  # Fallback model")
    print("\n" + "="*60)
    
    # Initialize agent
    print("\nInitializing Academic Agent...")
    agent = AcademicAgent()
    
    # Configuration
    scholarship_folder = "data/Delaney_Wings/Applications"
    model = "ollama/llama3.2:3b"
    fallback_model = "ollama/llama3:latest"
    max_wai_folders = 10  # Process first 10 WAI folders
    max_retries = 3
    skip_processed = True
    overwrite = False
    
    print(f"\nProcessing resumes from: {scholarship_folder}")
    print("="*60)
    
    # Process resumes
    result = agent.process_resumes(
        scholarship_folder=scholarship_folder,
        model=model,
        fallback_model=fallback_model,
        max_wai_folders=max_wai_folders,
        max_retries=max_retries,
        skip_processed=skip_processed,
        overwrite=overwrite
    )
    
    # Print summary
    print("\n" + "="*60)
    print("PROCESSING SUMMARY")
    print("="*60)
    print(f"Total WAI folders: {result.total}")
    print(f"Successfully processed: {result.successful}")
    print(f"Failed: {result.failed}")
    print(f"Skipped: {result.skipped}")
    print(f"\nTiming Information:")
    print(f"  Total duration: {result.duration:.2f} seconds")
    print(f"  Average per WAI: {result.average_per_wai:.2f} seconds")
    
    if result.errors:
        print(f"\nErrors encountered: {len(result.errors)}")
        for error in result.errors[:5]:  # Show first 5 errors
            print(f"  - {error.wai_number}: {error.error_type} - {error.error_message}")
    
    print("\nDone! Check the outputs folder for generated JSON files.")
    print("Example: outputs/academic/Delaney_Wings/75179/academic_analysis.json")
    print()


if __name__ == "__main__":
    main()

# Made with Bob

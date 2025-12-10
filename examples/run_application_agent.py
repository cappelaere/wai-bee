"""
Example script for running the Application Agent.

This script demonstrates how to use the Application Agent to process
scholarship applications and extract applicant information.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from agents.application_agent import ApplicationAgent


def main():
    """Run the Application Agent on Delaney Wings scholarship applications."""
      
    # Initialize the agent
    print("Initializing Application Agent...")
    agent = ApplicationAgent()
    
    # Define the scholarship folder path
    scholarship_folder = "data/Delaney_Wings/Applications"
    
    # Process applications
    # Set max_applications to limit the number processed (useful for testing)
    print(f"\nProcessing applications from: {scholarship_folder}")
    print("=" * 60)
    
    # result = agent.process_applications(
    #     scholarship_folder=scholarship_folder,
    #     max_applications=2,  # Process first 5 applications (remove or set to None for all)
    #     skip_processed=False,  # Skip applications that already have JSON output
    #     overwrite=True,  # Don't overwrite existing JSON files
    #     model="ollama/llama3.2:3b",  # Primary model to use
    #     fallback_model="ollama/llama3:latest",  # Fallback model if primary fails (optional)
    #     max_retries=3  # Number of retry attempts per model (default: 3)
    # )
    result = agent.analyze_application(
        wai_number="75179",
        scholarship_folder="data/Delaney_Wings",
        output_dir="outputs"
    )
    # Print summary
    print("\n" + "=" * 60)
    print("PROCESSING SUMMARY")
    print("=" * 60)
   
    print(f"result: {result}")


if __name__ == "__main__":
    main()

# Made with Bob

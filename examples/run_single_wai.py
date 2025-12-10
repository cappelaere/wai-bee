"""Run Recommendation Agent for a single WAI folder.

This script processes a single WAI folder for testing purposes.

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

from agents.recommendation_agent import RecommendationAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger()


def main():
    """Run the Recommendation Agent for a single WAI folder."""
    
    print("\n" + "="*60)
    print("Recommendation Agent - Single WAI Processing")
    print("="*60)
    
    # Initialize agent
    print("\nInitializing Recommendation Agent...")
    agent = RecommendationAgent()
    
    # Configuration for single WAI
    wai_number = "77747"
    scholarship_folder = Path("data/Delaney_Wings/Applications")
    model = "ollama/llama3.2:3b"
    fallback_model = "ollama/llama3:latest"
    min_files = 2
    max_retries = 3
    
    print(f"\nProcessing WAI: {wai_number}")
    print(f"Scholarship folder: {scholarship_folder}")
    print(f"Model: {model}")
    print("="*60)
    
    # Import utilities
    from utils.recommendation_scanner import (
        find_recommendation_files,
        read_recommendation_text,
        get_recommendation_output_path,
        validate_recommendation_files,
        get_scholarship_name_from_path
    )
    from utils.criteria_loader import load_criteria
    
    # Get scholarship name
    scholarship_name = get_scholarship_name_from_path(scholarship_folder)
    print(f"\nScholarship: {scholarship_name}")
    
    # Find recommendation files in unified output structure
    output_base = Path("outputs")
    rec_files = find_recommendation_files(
        output_base,
        scholarship_name,
        wai_number,
        max_files=2
    )
    
    # Validate files
    is_valid, error_msg = validate_recommendation_files(rec_files, min_files)
    if not is_valid:
        print(f"\nError: {error_msg}")
        return
    
    print(f"\nFound {len(rec_files)} recommendation files:")
    for f in rec_files:
        print(f"  - {f.name}")
    
    # Load criteria
    criteria = load_criteria(scholarship_folder, "recommendation")
    print(f"\nLoaded criteria ({len(criteria)} characters)")
    
    # Get criteria path for metadata
    if scholarship_folder.name == "Applications":
        criteria_folder = scholarship_folder.parent
    else:
        criteria_folder = scholarship_folder
    criteria_path = str(criteria_folder / "criteria" / "recommendation_criteria.txt")
    
    # Process with agent's internal method
    print(f"\nAnalyzing recommendations with {model}...")
    import time
    start_time = time.time()
    
    try:
        wai_folder = scholarship_folder / wai_number
        result = agent._process_single_wai(
            wai_folder=wai_folder,
            wai_number=wai_number,
            scholarship_name=scholarship_name,
            criteria=criteria,
            criteria_path=criteria_path,
            model=model,
            fallback_model=fallback_model,
            min_files=min_files,
            max_retries=max_retries
        )
        
        duration = time.time() - start_time
        
        print("\n" + "="*60)
        print("PROCESSING COMPLETE")
        print("="*60)
        print(f"Status: {'SUCCESS' if result else 'FAILED'}")
        print(f"Duration: {duration:.2f} seconds")
        
        if result:
            output_path = get_recommendation_output_path(
                Path("outputs"),
                scholarship_name,
                wai_number
            )
            print(f"\nOutput saved to:")
            print(f"  {output_path}")
            print("\nYou can view the JSON file to see the analysis results.")
        
    except Exception as e:
        print(f"\nError during processing: {e}")
        logger.exception("Processing failed")
    
    print()


if __name__ == "__main__":
    main()

# Made with Bob

"""
Example script demonstrating configuration usage.

This script shows how to use the centralized configuration
from environment variables (.env file).
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.config import config
from agents.application_agent import ApplicationAgent


def main():
    """Run the Application Agent using configuration from .env file."""
    
    print("="*60)
    print("WAI Scholarship Processing - Configuration Example")
    print("="*60)
    
    # Print current configuration
    print("\nCurrent Configuration:")
    config.print_config()
    
    # Validate configuration
    print("\nValidating configuration...")
    errors = config.validate()
    if errors:
        print("❌ Configuration errors found:")
        for error in errors:
            print(f"  - {error}")
        return
    print("✅ Configuration is valid")
    
    # Initialize agent
    print("\n" + "="*60)
    print("Initializing Application Agent...")
    print("="*60)
    agent = ApplicationAgent()
    
    # Process applications using config values
    scholarship_folder = str(config.DELANEY_WINGS_FOLDER / "Applications")
    
    print(f"\nProcessing applications from: {scholarship_folder}")
    print(f"Using model: {config.PRIMARY_MODEL}")
    print(f"Fallback model: {config.FALLBACK_MODEL}")
    print(f"Max retries: {config.MAX_RETRIES}")
    print(f"Max applications: {config.MAX_APPLICATIONS or 'unlimited'}")
    print(f"Skip processed: {config.SKIP_PROCESSED}")
    print(f"Overwrite: {config.OVERWRITE_EXISTING}")
    print("="*60)
    
    result = agent.process_applications(
        scholarship_folder=scholarship_folder,
        max_applications=config.MAX_APPLICATIONS,
        skip_processed=config.SKIP_PROCESSED,
        overwrite=config.OVERWRITE_EXISTING,
        output_dir=str(config.OUTPUTS_DIR),
        model=config.PRIMARY_MODEL,
        fallback_model=config.FALLBACK_MODEL,
        max_retries=config.MAX_RETRIES
    )
    
    # Print summary
    print("\n" + "="*60)
    print("PROCESSING SUMMARY")
    print("="*60)
    print(f"Total applications: {result.total}")
    print(f"Successfully processed: {result.successful}")
    print(f"Failed: {result.failed}")
    
    if result.total_duration:
        print(f"\nTiming Information:")
        print(f"  Total duration: {result.total_duration:.2f} seconds")
        if result.avg_duration_per_app:
            print(f"  Average per application: {result.avg_duration_per_app:.2f} seconds")
    
    if result.errors:
        print(f"\nErrors encountered:")
        for error in result.errors:
            print(f"  - WAI {error.wai_number}: {error.error_message}")
            if error.source_file:
                print(f"    File: {error.source_file}")
    
    print(f"\nDone! Check {config.OUTPUTS_DIR} for generated JSON files.")


if __name__ == "__main__":
    main()

# Made with Bob
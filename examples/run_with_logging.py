"""
Example script demonstrating centralized logging usage.

This script shows how to use the centralized logging configuration
for consistent logging across all agents and utilities.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logging_config import setup_logging, get_logger, log_performance
from utils.config import config
from agents.application_agent import ApplicationAgent
import time


def main():
    """Run the Application Agent with centralized logging."""
    
    # Setup logging first (this is done automatically on import, but can be customized)
    setup_logging(
        log_level=config.LOG_LEVEL,
        log_file=config.LOG_FILE,
        console_output=True,
        file_output=True
    )
    
    # Get logger for this module
    logger = get_logger(__name__)
    
    logger.info("="*60)
    logger.info("WAI Scholarship Processing - Logging Example")
    logger.info("="*60)
    
    # Log configuration
    logger.info("Configuration:")
    logger.info(f"  Primary Model: {config.PRIMARY_MODEL}")
    logger.info(f"  Fallback Model: {config.FALLBACK_MODEL}")
    logger.info(f"  Max Retries: {config.MAX_RETRIES}")
    logger.info(f"  Log Level: {config.LOG_LEVEL}")
    logger.info(f"  Log File: {config.LOG_FILE}")
    
    # Validate configuration
    logger.info("\nValidating configuration...")
    errors = config.validate()
    if errors:
        logger.error("Configuration errors found:")
        for error in errors:
            logger.error(f"  - {error}")
        return
    logger.info("✅ Configuration is valid")
    
    # Initialize agent
    logger.info("\n" + "="*60)
    logger.info("Initializing Application Agent...")
    logger.info("="*60)
    
    start_time = time.time()
    agent = ApplicationAgent()
    init_duration = time.time() - start_time
    log_performance(logger, "Agent initialization", init_duration)
    
    # Process applications
    scholarship_folder = str(config.get_scholarship_folder("Delaney_Wings") / "Applications")
    
    logger.info(f"\nProcessing applications from: {scholarship_folder}")
    logger.info("="*60)
    
    try:
        process_start = time.time()
        
        result = agent.process_applications(
            scholarship_folder=scholarship_folder,
            max_applications=config.MAX_APPLICATIONS or 5,  # Limit to 5 for demo
            skip_processed=config.SKIP_PROCESSED,
            overwrite=config.OVERWRITE_EXISTING,
            output_dir=str(config.OUTPUTS_DIR),
            model=config.PRIMARY_MODEL,
            fallback_model=config.FALLBACK_MODEL,
            max_retries=config.MAX_RETRIES
        )
        
        process_duration = time.time() - process_start
        log_performance(logger, "Application processing", process_duration)
        
        # Log summary
        logger.info("\n" + "="*60)
        logger.info("PROCESSING SUMMARY")
        logger.info("="*60)
        logger.info(f"Total applications: {result.total}")
        logger.info(f"Successfully processed: {result.successful}")
        logger.info(f"Failed: {result.failed}")
        
        if result.total_duration:
            logger.info(f"\nTiming Information:")
            logger.info(f"  Total duration: {result.total_duration:.2f} seconds")
            if result.avg_duration_per_app:
                logger.info(f"  Average per application: {result.avg_duration_per_app:.2f} seconds")
        
        if result.errors:
            logger.warning(f"\nErrors encountered: {len(result.errors)}")
            for error in result.errors:
                logger.error(f"  - WAI {error.wai_number}: {error.error_message}")
                if error.source_file:
                    logger.error(f"    File: {error.source_file}")
        
        logger.info(f"\n✅ Done! Check {config.OUTPUTS_DIR} for generated JSON files.")
        logger.info(f"📄 Log file: {config.LOG_FILE}")
        
    except Exception as e:
        logger.error("Fatal error during processing", exc_info=True)
        raise


if __name__ == "__main__":
    main()

# Made with Bob
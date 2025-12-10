"""Logging configuration for the bee_agents application.

This module provides centralized logging configuration for the chat API
and related components.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-09
Version: 1.0.0
License: MIT
"""

import logging


def setup_logging(name) -> logging.Logger:
    """Configure logging for the application.
    
    Sets up the root logger with INFO level and a standard format,
    then reduces verbosity for noisy third-party loggers.
    
    Returns:
        Logger instance for the calling module
    """
    # Configure root logger
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        force=True
    )
    
    # Reduce verbosity of noisy third-party loggers
    logging.getLogger("beeai_framework").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    
    # Return logger for the calling module
    return logging.getLogger(name)


# Module-level logger for this file
# logger = setup_logging()

# Made with Bob

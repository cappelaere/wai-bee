"""Centralized logging configuration for WAI scholarship processing system.

This module provides a unified logging setup for all agents and utilities,
with support for console and file logging, log rotation, and configurable
log levels.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-06
Version: 1.0.0
License: MIT

Example:
    >>> from utils.logging_config import setup_logging, get_logger
    >>> 
    >>> # Setup logging once at application start
    >>> setup_logging()
    >>> 
    >>> # Get logger in any module
    >>> logger = get_logger(__name__)
    >>> logger.info("Processing started")
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional

from .config import config


# Global flag to track if logging has been configured
_logging_configured = False


def setup_logging(
    log_level: Optional[str] = None,
    log_file: Optional[str] = None,
    log_format: Optional[str] = None,
    console_output: bool = True,
    file_output: bool = True,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    force: bool = False
) -> None:
    """Setup centralized logging configuration.
    
    Configures logging with both console and file handlers, using settings
    from environment variables or provided parameters.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
            If None, uses config.LOG_LEVEL.
        log_file: Path to log file. If None, uses config.LOG_FILE.
        log_format: Log message format. If None, uses config.LOG_FORMAT.
        console_output: Enable console logging (default: True).
        file_output: Enable file logging (default: True).
        max_bytes: Maximum size of log file before rotation (default: 10MB).
        backup_count: Number of backup log files to keep (default: 5).
        force: Force reconfiguration even if already configured (default: False).
    
    Example:
        >>> setup_logging(log_level="DEBUG", console_output=True)
        >>> logger = get_logger(__name__)
        >>> logger.debug("Debug message")
    
    Note:
        This function should be called once at application startup.
        Subsequent calls will be ignored unless force=True.
    """
    global _logging_configured
    
    if _logging_configured and not force:
        return
    
    # Use config values if not provided
    log_level = log_level or config.LOG_LEVEL
    log_file = log_file or config.LOG_FILE
    log_format = log_format or config.LOG_FORMAT
    
    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Create root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()
    
    # Create formatter
    formatter = logging.Formatter(log_format)
    
    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if file_output and log_file:
        # Ensure log directory exists
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Suppress noisy third-party loggers
    logging.getLogger('LiteLLM').setLevel(logging.WARNING)
    logging.getLogger('LiteLLM.utils').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    logging.getLogger('docling').setLevel(logging.WARNING)
    logging.getLogger('presidio-analyzer').setLevel(logging.WARNING)
    
    # Disable LiteLLM's internal logging completely for cleaner output
    litellm_logger = logging.getLogger('LiteLLM')
    litellm_logger.propagate = False
    
    # Mark as configured
    _logging_configured = True
    
    # Log initial message
    root_logger.info("="*60)
    root_logger.info("Logging configured successfully")
    root_logger.info(f"Log level: {log_level}")
    if file_output and log_file:
        root_logger.info(f"Log file: {log_file}")
    root_logger.info("="*60)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a module.
    
    Args:
        name: Logger name, typically __name__ of the calling module.
    
    Returns:
        Logger instance configured with the application settings.
    
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing application")
        >>> logger.error("Failed to process", exc_info=True)
    
    Note:
        If setup_logging() hasn't been called, this will use Python's
        default logging configuration.
    """
    return logging.getLogger(name)


def reconfigure_logging(
    log_level: Optional[str] = None,
    console_output: Optional[bool] = None,
    file_output: Optional[bool] = None
) -> None:
    """Reconfigure logging at runtime.
    
    Allows changing log level or output destinations without restarting
    the application.
    
    Args:
        log_level: New logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        console_output: Enable/disable console logging.
        file_output: Enable/disable file logging.
    
    Example:
        >>> # Start with INFO level
        >>> setup_logging(log_level="INFO")
        >>> 
        >>> # Switch to DEBUG for troubleshooting
        >>> reconfigure_logging(log_level="DEBUG")
    """
    global _logging_configured
    
    root_logger = logging.getLogger()
    
    # Update log level
    if log_level:
        numeric_level = getattr(logging, log_level.upper(), logging.INFO)
        root_logger.setLevel(numeric_level)
        for handler in root_logger.handlers:
            handler.setLevel(numeric_level)
        root_logger.info(f"Log level changed to: {log_level}")
    
    # Update console output
    if console_output is not None:
        console_handlers = [h for h in root_logger.handlers 
                          if isinstance(h, logging.StreamHandler) 
                          and not isinstance(h, RotatingFileHandler)]
        
        if console_output and not console_handlers:
            # Add console handler
            formatter = logging.Formatter(config.LOG_FORMAT)
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(root_logger.level)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
            root_logger.info("Console logging enabled")
        elif not console_output and console_handlers:
            # Remove console handlers
            for handler in console_handlers:
                root_logger.removeHandler(handler)
    
    # Update file output
    if file_output is not None:
        file_handlers = [h for h in root_logger.handlers 
                        if isinstance(h, RotatingFileHandler)]
        
        if file_output and not file_handlers and config.LOG_FILE:
            # Add file handler
            log_path = Path(config.LOG_FILE)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            formatter = logging.Formatter(config.LOG_FORMAT)
            file_handler = RotatingFileHandler(
                config.LOG_FILE,
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(root_logger.level)
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            root_logger.info(f"File logging enabled: {config.LOG_FILE}")
        elif not file_output and file_handlers:
            # Remove file handlers
            for handler in file_handlers:
                root_logger.removeHandler(handler)
                handler.close()


def log_exception(logger: logging.Logger, message: str, exc: Exception) -> None:
    """Log an exception with full traceback.
    
    Args:
        logger: Logger instance to use.
        message: Context message describing what was being done.
        exc: Exception that was caught.
    
    Example:
        >>> logger = get_logger(__name__)
        >>> try:
        ...     risky_operation()
        ... except Exception as e:
        ...     log_exception(logger, "Failed to process application", e)
    """
    logger.error(f"{message}: {str(exc)}", exc_info=True)


def log_performance(logger: logging.Logger, operation: str, duration: float) -> None:
    """Log performance metrics for an operation.
    
    Args:
        logger: Logger instance to use.
        operation: Name of the operation.
        duration: Duration in seconds.
    
    Example:
        >>> import time
        >>> logger = get_logger(__name__)
        >>> start = time.time()
        >>> process_application()
        >>> log_performance(logger, "Application processing", time.time() - start)
    """
    logger.info(f"Performance: {operation} completed in {duration:.2f}s")


# Auto-configure logging on module import if not already configured
if not _logging_configured:
    try:
        setup_logging()
    except Exception as e:
        # Fallback to basic config if setup fails
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        logging.warning(f"Failed to setup logging from config: {e}")


# Made with Bob
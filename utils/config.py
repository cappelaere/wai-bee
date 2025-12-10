"""Configuration management using environment variables.

This module loads configuration from .env file and provides
typed access to configuration values with sensible defaults.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-06
Version: 1.0.0
License: MIT
"""

import os
from pathlib import Path
from typing import Optional, List
from dotenv import load_dotenv

# Load .env file from project root
load_dotenv()


class Config:
    """Configuration class for WAI scholarship processing system.
    
    Loads configuration from environment variables with fallback defaults.
    All values are loaded once at module import time.
    
    Example:
        >>> from utils.config import config
        >>> print(config.PRIMARY_MODEL)
        'ollama/llama3.2:1b'
        >>> print(config.MAX_RETRIES)
        3
    """
    
    # LLM Configuration
    PRIMARY_MODEL: str = os.getenv("PRIMARY_MODEL", "ollama/llama3.2:1b")
    FALLBACK_MODEL: str = os.getenv("FALLBACK_MODEL", "ollama/llama3:latest")
    LARGE_MODEL: str = os.getenv("LARGE_MODEL", "ollama/llama3.2:3b")
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "4000"))
    
    # OpenAI Configuration (optional)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    
    # Processing Configuration
    MAX_APPLICATIONS: Optional[int] = None
    _max_apps_env = os.getenv("MAX_APPLICATIONS")
    if _max_apps_env and _max_apps_env.lower() != "none":
        try:
            MAX_APPLICATIONS = int(_max_apps_env)
        except ValueError:
            MAX_APPLICATIONS = None
    MAX_FILES_PER_FOLDER: int = int(os.getenv("MAX_FILES_PER_FOLDER", "5"))
    SKIP_PROCESSED: bool = os.getenv("SKIP_PROCESSED", "true").lower() == "true"
    OVERWRITE_EXISTING: bool = os.getenv("OVERWRITE_EXISTING", "false").lower() == "true"
    
    # Parallel Processing
    ENABLE_PARALLEL: bool = os.getenv("ENABLE_PARALLEL", "true").lower() == "true"
    MAX_WORKERS: int = int(os.getenv("MAX_WORKERS", "3"))
    
    # Directory Configuration
    DATA_DIR: Path = Path(os.getenv("DATA_DIR", "data"))
    OUTPUTS_DIR: Path = Path(os.getenv("OUTPUTS_DIR", "outputs"))
    SCHEMAS_DIR: Path = Path(os.getenv("SCHEMAS_DIR", "schemas"))
    TEMPLATES_DIR: Path = Path(os.getenv("TEMPLATES_DIR", "templates"))
    
    # PII Redaction Configuration
    PII_SCORE_THRESHOLD: float = float(os.getenv("PII_SCORE_THRESHOLD", "0.5"))
    PII_EXCLUDE_ENTITIES: List[str] = (
        os.getenv("PII_EXCLUDE_ENTITIES", "PERSON,LOCATION,NRP").split(",")
    )
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Optional[str] = os.getenv("LOG_FILE", "logs/wai_processing.log")
    LOG_FORMAT: str = os.getenv(
        "LOG_FORMAT",
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Scholarship Folders
    DELANEY_WINGS_FOLDER: Path = Path(os.getenv("DELANEY_WINGS_FOLDER", "data/Delaney_Wings"))
    EVANS_WINGS_FOLDER: Path = Path(os.getenv("EVANS_WINGS_FOLDER", "data/Evans_Wings"))
    
    @classmethod
    def get_scholarship_folder(cls, scholarship_name: str) -> Optional[Path]:
        """Get scholarship folder path by name.
        
        Args:
            scholarship_name: Name of scholarship (e.g., "Delaney_Wings", "Evans_Wings").
        
        Returns:
            Path to scholarship folder, or None if not found.
        
        Example:
            >>> folder = Config.get_scholarship_folder("Delaney_Wings")
            >>> print(folder)
            data/Delaney_Wings
        """
        if scholarship_name == "Delaney_Wings":
            return cls.DELANEY_WINGS_FOLDER
        elif scholarship_name == "Evans_Wings":
            return cls.EVANS_WINGS_FOLDER
        return None
    
    @classmethod
    def validate(cls) -> List[str]:
        """Validate configuration and return list of issues.
        
        Returns:
            List of validation error messages. Empty list if all valid.
        
        Example:
            >>> errors = Config.validate()
            >>> if errors:
            ...     print("Configuration errors:", errors)
        """
        errors = []
        
        # Check required directories exist
        if not cls.DATA_DIR.exists():
            errors.append(f"Data directory does not exist: {cls.DATA_DIR}")
        
        if not cls.SCHEMAS_DIR.exists():
            errors.append(f"Schemas directory does not exist: {cls.SCHEMAS_DIR}")
        
        # Validate numeric ranges
        if cls.MAX_RETRIES < 1:
            errors.append(f"MAX_RETRIES must be >= 1, got {cls.MAX_RETRIES}")
        
        if cls.LLM_TEMPERATURE < 0 or cls.LLM_TEMPERATURE > 2:
            errors.append(f"LLM_TEMPERATURE must be 0-2, got {cls.LLM_TEMPERATURE}")
        
        if cls.MAX_WORKERS < 1:
            errors.append(f"MAX_WORKERS must be >= 1, got {cls.MAX_WORKERS}")
        
        if cls.PII_SCORE_THRESHOLD < 0 or cls.PII_SCORE_THRESHOLD > 1:
            errors.append(f"PII_SCORE_THRESHOLD must be 0-1, got {cls.PII_SCORE_THRESHOLD}")
        
        return errors
    
    @classmethod
    def print_config(cls):
        """Print current configuration (for debugging).
        
        Example:
            >>> Config.print_config()
            Configuration:
            PRIMARY_MODEL: ollama/llama3.2:1b
            ...
        """
        print("Configuration:")
        print(f"  PRIMARY_MODEL: {cls.PRIMARY_MODEL}")
        print(f"  FALLBACK_MODEL: {cls.FALLBACK_MODEL}")
        print(f"  LARGE_MODEL: {cls.LARGE_MODEL}")
        print(f"  MAX_RETRIES: {cls.MAX_RETRIES}")
        print(f"  LLM_TEMPERATURE: {cls.LLM_TEMPERATURE}")
        print(f"  MAX_APPLICATIONS: {cls.MAX_APPLICATIONS}")
        print(f"  SKIP_PROCESSED: {cls.SKIP_PROCESSED}")
        print(f"  ENABLE_PARALLEL: {cls.ENABLE_PARALLEL}")
        print(f"  MAX_WORKERS: {cls.MAX_WORKERS}")
        print(f"  DATA_DIR: {cls.DATA_DIR}")
        print(f"  OUTPUTS_DIR: {cls.OUTPUTS_DIR}")
        print(f"  PII_SCORE_THRESHOLD: {cls.PII_SCORE_THRESHOLD}")
        print(f"  LOG_LEVEL: {cls.LOG_LEVEL}")


# Global config instance
config = Config()


# Validate configuration on import
_validation_errors = config.validate()
if _validation_errors:
    import warnings
    for error in _validation_errors:
        warnings.warn(f"Configuration warning: {error}")


# Made with Bob
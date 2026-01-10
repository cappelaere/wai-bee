"""Configuration management using environment variables.

This module loads configuration from .env file and provides
typed access to configuration values with sensible defaults.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-06
Version: 2.0.0 - Updated for WAI-general-2025 folder structure
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
    
    Folder Structure (WAI-general-2025/):
        - data/{scholarship}/{WAI-ID}/     Application files (PDFs, etc.)
        - config/{scholarship}/            Config files (config.yml, agents.json, prompts/, schemas_generated/)
        - output/{scholarship}/{WAI-ID}/   Processing outputs (analysis JSON files)
        - logs/                            Processing logs
    
    Example:
        >>> from utils.config import config
        >>> print(config.PRIMARY_MODEL)
        'ollama/llama3.2:1b'
        >>> print(config.get_config_folder("Delaney_Wings"))
        WAI-general-2025/config/Delaney_Wings
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
    
    # Directory Configuration - WAI-general-2025 structure
    BASE_DIR: Path = Path(os.getenv("WAI_BASE_DIR", "WAI-general-2025"))
    DATA_DIR: Path = BASE_DIR / "data"
    CONFIG_DIR: Path = BASE_DIR / "config"
    OUTPUTS_DIR: Path = BASE_DIR / "output"
    LOGS_DIR: Path = BASE_DIR / "logs"
    
    # Project-level directories (not under WAI-general-2025)
    SCHEMAS_DIR: Path = Path(os.getenv("SCHEMAS_DIR", "schemas"))
    TEMPLATES_DIR: Path = Path(os.getenv("TEMPLATES_DIR", "templates"))
    
    # PII Redaction Configuration
    PII_SCORE_THRESHOLD: float = float(os.getenv("PII_SCORE_THRESHOLD", "0.5"))
    PII_EXCLUDE_ENTITIES: List[str] = (
        os.getenv("PII_EXCLUDE_ENTITIES", "PERSON,LOCATION,NRP").split(",")
    )
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: Optional[str] = os.getenv("LOG_FILE", str(BASE_DIR / "logs" / "wai_processing.log"))
    LOG_FORMAT: str = os.getenv(
        "LOG_FORMAT",
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    @classmethod
    def get_data_folder(cls, scholarship_name: str) -> Path:
        """Get data folder path for a scholarship (application files).
        
        Args:
            scholarship_name: Name of scholarship (e.g., "Delaney_Wings").
        
        Returns:
            Path to data folder (DATA_DIR / scholarship_name).
        
        Example:
            >>> folder = Config.get_data_folder("Delaney_Wings")
            >>> print(folder)
            WAI-general-2025/data/Delaney_Wings
        """
        return cls.DATA_DIR / scholarship_name
    
    @classmethod
    def get_config_folder(cls, scholarship_name: str) -> Path:
        """Get config folder path for a scholarship (config.yml, agents.json, prompts/, schemas_generated/).
        
        Args:
            scholarship_name: Name of scholarship (e.g., "Delaney_Wings").
        
        Returns:
            Path to config folder (CONFIG_DIR / scholarship_name).
        
        Example:
            >>> folder = Config.get_config_folder("Delaney_Wings")
            >>> print(folder)
            WAI-general-2025/config/Delaney_Wings
        """
        return cls.CONFIG_DIR / scholarship_name
    
    @classmethod
    def get_output_folder(cls, scholarship_name: str) -> Path:
        """Get output folder path for a scholarship (processing results).
        
        Args:
            scholarship_name: Name of scholarship (e.g., "Delaney_Wings").
        
        Returns:
            Path to output folder (OUTPUTS_DIR / scholarship_name).
        
        Example:
            >>> folder = Config.get_output_folder("Delaney_Wings")
            >>> print(folder)
            WAI-general-2025/output/Delaney_Wings
        """
        return cls.OUTPUTS_DIR / scholarship_name
    
    @classmethod
    def get_scholarship_folder(cls, scholarship_name: str) -> Path:
        """Get scholarship config folder path by name.
        
        This is the primary folder containing config.yml and other configuration.
        For backwards compatibility, this returns the config folder.
        
        Args:
            scholarship_name: Name of scholarship (e.g., "Delaney_Wings", "Evans_Wings").
        
        Returns:
            Path to scholarship config folder (CONFIG_DIR / scholarship_name).
        
        Example:
            >>> folder = Config.get_scholarship_folder("Delaney_Wings")
            >>> print(folder)
            WAI-general-2025/config/Delaney_Wings
        """
        return cls.get_config_folder(scholarship_name)
    
    @classmethod
    def get_applicant_data_folder(cls, scholarship_name: str, wai_id: str) -> Path:
        """Get applicant data folder (input application files).
        
        Args:
            scholarship_name: Name of scholarship.
            wai_id: WAI applicant ID.
        
        Returns:
            Path to applicant data folder.
        
        Example:
            >>> folder = Config.get_applicant_data_folder("Delaney_Wings", "75179")
            >>> print(folder)
            WAI-general-2025/data/Delaney_Wings/75179
        """
        return cls.DATA_DIR / scholarship_name / wai_id
    
    @classmethod
    def get_logs_folder(cls, scholarship_name: str) -> Path:
        """Get logs folder path for a scholarship.
        
        Args:
            scholarship_name: Name of scholarship (e.g., "Delaney_Wings").
        
        Returns:
            Path to logs folder (LOGS_DIR / scholarship_name).
        
        Example:
            >>> folder = Config.get_logs_folder("Delaney_Wings")
            >>> print(folder)
            WAI-general-2025/logs/Delaney_Wings
        """
        return cls.LOGS_DIR / scholarship_name
    
    @classmethod
    def get_applicant_output_folder(cls, scholarship_name: str, wai_id: str) -> Path:
        """Get applicant output folder (processing results).
        
        Args:
            scholarship_name: Name of scholarship.
            wai_id: WAI applicant ID.
        
        Returns:
            Path to applicant output folder.
        
        Example:
            >>> folder = Config.get_applicant_output_folder("Delaney_Wings", "75179")
            >>> print(folder)
            WAI-general-2025/output/Delaney_Wings/75179
        """
        return cls.OUTPUTS_DIR / scholarship_name / wai_id
    
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
        if not cls.BASE_DIR.exists():
            errors.append(f"Base directory does not exist: {cls.BASE_DIR}")
        
        if not cls.DATA_DIR.exists():
            errors.append(f"Data directory does not exist: {cls.DATA_DIR}")
        
        if not cls.CONFIG_DIR.exists():
            errors.append(f"Config directory does not exist: {cls.CONFIG_DIR}")
        
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
        print(f"  BASE_DIR: {cls.BASE_DIR}")
        print(f"  DATA_DIR: {cls.DATA_DIR}")
        print(f"  CONFIG_DIR: {cls.CONFIG_DIR}")
        print(f"  OUTPUTS_DIR: {cls.OUTPUTS_DIR}")
        print(f"  LOGS_DIR: {cls.LOGS_DIR}")
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

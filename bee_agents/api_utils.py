"""Shared utilities for API routers.

This module contains shared functions used by multiple routers to avoid circular imports.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-16
Version: 1.0.0
License: MIT
"""

from typing import Dict
from pathlib import Path
from fastapi import HTTPException

from .data_service import DataService


# Global data services dictionary (shared with api.py)
data_services: Dict[str, DataService] = {}


def get_data_service(scholarship: str) -> DataService:
    """Get the data service for a specific scholarship.
    
    Args:
        scholarship: Name of the scholarship
        
    Returns:
        DataService instance for the scholarship
        
    Raises:
        HTTPException: If scholarship not found or not available
    """
    if scholarship not in data_services:
        raise HTTPException(
            status_code=404,
            detail=f"Scholarship '{scholarship}' not found. Available: {', '.join(data_services.keys())}"
        )
    return data_services[scholarship]


def get_scholarship_config_path(scholarship_name: str) -> Path:
    """Get path to canonical config.yml for a scholarship."""
    return Path("data") / scholarship_name / "config.yml"


def load_scholarship_config(scholarship_name: str) -> dict:
    """Load canonical scholarship config."""
    import yaml
    from fastapi import HTTPException
    
    config_path = get_scholarship_config_path(scholarship_name)
    if not config_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Config file not found for scholarship {scholarship_name}: {config_path}",
        )
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        return config
    except Exception as e:
        raise HTTPException(status_code=500, detail="Failed to load scholarship config")

# Made with Bob

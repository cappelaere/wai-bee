"""Validation service for application processing.

This module handles validation of extracted application data and attachments.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-07
Version: 1.0.0
License: MIT
"""

import logging
from pathlib import Path
from typing import List, Optional

from models.application_data import ApplicationData

logger = logging.getLogger(__name__)


class ValidationService:
    """Service for validating application data and attachments."""
    
    @staticmethod
    def check_attachment_files(wai_folder: Path, app_file_name: str) -> List[dict]:
        """Check for required attachment files in the WAI folder.
        
        Args:
            wai_folder: Path to the WAI folder containing application files.
            app_file_name: Name of the main application file to exclude.
        
        Returns:
            List of dicts with file info: [{"name": str, "size": int, "valid": bool, "error": str}, ...]
        """
        attachment_file_details = []
        
        if not wai_folder.exists():
            logger.warning(f"WAI folder not found: {wai_folder}")
            return attachment_file_details
        
        # Get all files except the application PDF
        for file_path in wai_folder.iterdir():
            if file_path.is_file() and file_path.name != app_file_name and not file_path.name.startswith('.'):
                file_size = file_path.stat().st_size
                file_info = {
                    "name": file_path.name,
                    "size": file_size,
                    "valid": True,
                    "error": None
                }
                
                # Check if file is valid
                if file_size == 0:
                    file_info["valid"] = False
                    file_info["error"] = "File is empty (0 bytes)"
                elif not file_path.name or file_path.name.strip() == "":
                    file_info["valid"] = False
                    file_info["error"] = "Filename is empty or null"
                
                attachment_file_details.append(file_info)
                
                # Log file details
                status = "✓" if file_info["valid"] else "✗"
                logger.info(f"  {status} {file_path.name}: {file_size:,} bytes")
                if not file_info["valid"]:
                    logger.warning(f"    Error: {file_info['error']}")
        
        logger.info(f"Found {len(attachment_file_details)} attachment files")
        return attachment_file_details
    
    @staticmethod
    def validate_extracted_data(
        extracted_data: ApplicationData,
        attachment_file_details: List[dict]
    ) -> bool:
        """Validate extracted application data and attachments.
        
        Args:
            extracted_data: The extracted application data to validate.
            attachment_file_details: List of attachment file details.
        
        Returns:
            True if validation passed, False if there are errors.
        """
        logger.info("Validating required fields and attachments...")
        extracted_data.validate_required_fields(attachment_file_details=attachment_file_details)
        
        if extracted_data.has_errors:
            logger.error(f"Validation failed for {extracted_data.wai_number}:")
            for error in extracted_data.validation_errors:
                logger.error(f"  - {error}")
            return False
        
        logger.info("✓ All required fields and attachments validated successfully")
        return True


# Made with Bob
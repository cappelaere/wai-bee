"""Validation service for application processing.

This module handles validation of extracted application data and attachments.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-07
Version: 1.0.0
License: MIT
"""

import logging
import re
from pathlib import Path
from typing import List, Optional

from models.application_data import ApplicationData

logger = logging.getLogger(__name__)


class ValidationService:
    """Service for validating application data and attachments."""
    
    # Maximum number of attachments to consider for validation logic.
    # This aligns with the 5 required attachments in ApplicationData.validate_required_fields.
    MAX_ATTACHMENTS_FOR_VALIDATION = 5
    
    @staticmethod
    def check_attachment_files(wai_folder: Path, app_file_name: str) -> List[dict]:
        """Check for required attachment files in the WAI folder.
        
        Args:
            wai_folder: Path to the WAI folder containing application files.
            app_file_name: Name of the main application file to exclude.
        
        Returns:
            List of dicts with file info: [{"name": str, "size": int, "valid": bool, "error": str}, ...]
        """
        attachment_file_details: List[dict] = []
        
        if not wai_folder.exists():
            logger.warning(f"WAI folder not found: {wai_folder}")
            return attachment_file_details
        
        # Attachments follow the pattern:
        #   {WAI Number}_{number}_{number}.{ext}
        # e.g. 101866_24_1.pdf, 101866_24_10.pdf
        # We only consider files matching this pattern (and not the main app file),
        # and we sort them numerically by the two numeric components.
        wai_number = wai_folder.name
        pattern = re.compile(rf"^{re.escape(wai_number)}_(\d+)_(\d+)\.", re.IGNORECASE)
        
        candidates: List[tuple[Path, int, int]] = []
        
        for file_path in wai_folder.iterdir():
            if not file_path.is_file():
                continue
            if file_path.name == app_file_name or file_path.name.startswith('.'):
                continue
            
            match = pattern.match(file_path.name)
            if not match:
                # Ignore non-attachment files (e.g., misnamed or helper files)
                continue
            
            major_idx = int(match.group(1))
            minor_idx = int(match.group(2))
            candidates.append((file_path, major_idx, minor_idx))
        
        # Sort attachments by their numeric indices for deterministic ordering
        candidates.sort(key=lambda item: (item[1], item[2]))
        
        # Only consider the first N attachments in this sorted order for validation
        max_n = ValidationService.MAX_ATTACHMENTS_FOR_VALIDATION
        if len(candidates) > max_n:
            logger.info(
                f"Found {len(candidates)} matching attachment files; "
                f"limiting validation to first {max_n} by numeric order"
            )
            candidates = candidates[:max_n]
        
        for file_path, major_idx, minor_idx in candidates:
            file_size = file_path.stat().st_size
            file_info = {
                "name": file_path.name,
                "size": file_size,
                "valid": True,
                "error": None,
                "order": {
                    "group_index": major_idx,
                    "file_index": minor_idx,
                },
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
            logger.info(
                f"  {status} {file_path.name}: {file_size:,} bytes "
                f"(group={major_idx}, index={minor_idx})"
            )
            if not file_info["valid"]:
                logger.warning(f"    Error: {file_info['error']}")
        
        logger.info(f"Found {len(attachment_file_details)} attachment files matching pattern {wai_number}_<n>_<m>")
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
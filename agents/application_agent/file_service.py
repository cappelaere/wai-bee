"""File service for application processing.

This module handles file operations for application processing.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-07
Version: 1.0.0
License: MIT
"""

import json
import logging
from pathlib import Path
from typing import Optional, Any

from models.application_data import ApplicationData
from utils.file_identifier import get_output_json_path, is_already_processed
from utils.json_writer import save_application_json

logger = logging.getLogger(__name__)


class FileService:
    """Service for file operations in application processing."""
    
    @staticmethod
    def check_processing_status(
        app_file: Path,
        output_dir: str,
        skip_processed: bool
    ) -> tuple[bool, bool, Optional[Path], Optional[Path]]:
        """Check if application has already been processed.
        
        Args:
            app_file: Path to the application file.
            output_dir: Base output directory.
            skip_processed: Whether to skip already processed files.
        
        Returns:
            Tuple of (extraction_exists, analysis_exists, output_path, analysis_path)
        """
        output_path = get_output_json_path(app_file, output_dir)
        analysis_path = output_path.parent / "application_analysis.json"
        
        extraction_exists = is_already_processed(app_file)
        analysis_exists = analysis_path.exists()
        
        return extraction_exists, analysis_exists, output_path, analysis_path
    
    @staticmethod
    def load_existing_extraction(output_path: Path) -> Optional[ApplicationData]:
        """Load existing extraction data from JSON file.
        
        Args:
            output_path: Path to the extraction JSON file.
        
        Returns:
            ApplicationData if file exists and is valid, None otherwise.
        """
        try:
            if output_path.exists():
                with open(output_path, 'r') as f:
                    data = json.load(f)
                return ApplicationData(**data)
        except Exception as e:
            logger.error(f"Failed to load existing extraction: {e}")
        return None
    
    @staticmethod
    def save_extraction(
        extracted_data: ApplicationData,
        output_path: Path,
        overwrite: bool
    ) -> bool:
        """Save extraction data to JSON file.
        
        Args:
            extracted_data: The application data to save.
            output_path: Path where to save the JSON file.
            overwrite: Whether to overwrite existing files.
        
        Returns:
            True if save was successful or file already exists, False otherwise.
        """
        logger.info(f"Saving extraction to: {output_path.name}")
        
        save_result = save_application_json(extracted_data, output_path, overwrite)
        if not save_result and not output_path.exists():
            # Only fail if save failed AND file doesn't exist
            logger.error("Failed to save extraction JSON file")
            return False
        
        return True
    
    @staticmethod
    def save_analysis(
        analysis: Any,
        analysis_path: Path
    ) -> bool:
        """Save analysis data to JSON file.
        
        Args:
            analysis: The application analysis to save.
            analysis_path: Path where to save the analysis JSON file.
        
        Returns:
            True if save was successful, False otherwise.
        """
        try:
            with open(analysis_path, 'w', encoding='utf-8') as f:
                if hasattr(analysis, "model_dump"):
                    payload = analysis.model_dump()
                else:
                    payload = analysis
                json.dump(payload, f, indent=2, ensure_ascii=False, default=str)
            logger.info(f"Saved analysis to: {analysis_path.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to save analysis JSON: {e}")
            return False


# Made with Bob
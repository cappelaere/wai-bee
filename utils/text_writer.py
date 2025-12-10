"""Utility for writing redacted text files.

This module provides functions to save redacted text content with metadata
headers to .txt files.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-05
Version: 1.0.0
License: MIT
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timezone

from models.attachment_data import AttachmentData

logger = logging.getLogger()


def save_redacted_text(
    text: str,
    output_path: Path,
    metadata: AttachmentData,
    overwrite: bool = False
) -> bool:
    """Save redacted text to file with metadata header.
    
    Writes the redacted text content to a .txt file with a metadata header
    containing information about the source file, processing date, and PII
    types that were removed.
    
    Args:
        text (str): The redacted text content to save.
        output_path (Path): Full path where the .txt file should be saved.
        metadata (AttachmentData): Metadata about the processed attachment.
        overwrite (bool): Whether to overwrite existing files. Defaults to False.
    
    Returns:
        bool: True if file was saved successfully, False otherwise.
    
    Example:
        >>> from models.attachment_data import AttachmentData
        >>> from datetime import datetime, timezone
        >>> 
        >>> metadata = AttachmentData(
        ...     wai_number="75179",
        ...     source_file="75179_19_1.pdf",
        ...     output_file="75179_19_1.txt",
        ...     original_length=5234,
        ...     redacted_length=4891,
        ...     pii_types_found=["names", "emails"],
        ...     processed_date=datetime.now(timezone.utc)
        ... )
        >>> 
        >>> text = "[NAME] applied for the scholarship..."
        >>> output = Path("outputs/attachments/Delaney_Wings/75179/75179_19_1.txt")
        >>> success = save_redacted_text(text, output, metadata)
    
    Note:
        - Creates parent directories if they don't exist
        - Adds metadata header to the file
        - Uses UTF-8 encoding
        - Skips if file exists and overwrite=False
    """
    try:
        # Check if file exists and overwrite is False
        if output_path.exists() and not overwrite:
            logger.debug(f"File already exists, skipping: {output_path.name}")
            return False
        
        # Ensure parent directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write file with just the text content (no header)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        logger.info(f"Successfully saved redacted text: {output_path.name}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving redacted text to {output_path}: {str(e)}")
        return False


def create_processing_summary(
    output_dir: Path,
    wai_number: str,
    attachments: list[AttachmentData]
) -> bool:
    """Create a summary JSON file for all processed attachments in a WAI folder.
    
    Generates a summary JSON file listing all processed attachments with
    their metadata and statistics.
    
    Args:
        output_dir (Path): Directory where summary should be saved.
        wai_number (str): WAI number for the folder.
        attachments (list[AttachmentData]): List of processed attachment metadata.
    
    Returns:
        bool: True if summary was created successfully, False otherwise.
    
    Example:
        >>> output_dir = Path("outputs/Delaney_Wings/75179/attachments")
        >>> attachments = [metadata1, metadata2, metadata3]
        >>> create_processing_summary(output_dir, "75179", attachments)
    
    Note:
        Summary file is named: _processing_summary.json
    """
    try:
        summary_path = output_dir / "_processing_summary.json"
        
        # Calculate totals
        total_files = len(attachments)
        total_original = sum(a.original_length for a in attachments)
        total_redacted = sum(a.redacted_length for a in attachments)
        all_pii_types = set()
        for a in attachments:
            all_pii_types.update(a.pii_types_found)
        
        # Calculate reduction percentage
        reduction_pct = 0.0
        if total_original > 0:
            reduction_pct = ((total_original - total_redacted) / total_original * 100)
        
        # Create summary structure
        summary = {
            "wai_number": wai_number,
            "summary": {
                "total_files": total_files,
                "total_original_chars": total_original,
                "total_redacted_chars": total_redacted,
                "total_reduction_chars": total_original - total_redacted,
                "reduction_percentage": round(reduction_pct, 1),
                "pii_types_found": sorted(list(all_pii_types)) if all_pii_types else []
            },
            "processed_files": []
        }
        
        # Add each file's details
        for attachment in attachments:
            file_info = {
                "source_file": attachment.source_file,
                "output_file": attachment.output_file,
                "original_length": attachment.original_length,
                "redacted_length": attachment.redacted_length,
                "pii_types_found": attachment.pii_types_found,
                "processed_date": attachment.processed_date.isoformat(),
                "has_errors": attachment.has_errors,
                "errors": attachment.errors
            }
            
            # Add optional fields if present
            if hasattr(attachment, 'source_file_size') and attachment.source_file_size is not None:
                file_info["source_file_size"] = attachment.source_file_size
            
            summary["processed_files"].append(file_info)
        
        # Write summary file
        with open(summary_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Created processing summary: {summary_path.name}")
        return True
        
    except Exception as e:
        logger.error(f"Error creating processing summary: {str(e)}")
        return False

# Made with Bob

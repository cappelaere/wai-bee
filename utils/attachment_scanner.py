"""Utility for scanning and identifying attachment files.

This module provides functions to find attachment files in WAI folders,
excluding the main application PDF file.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-05
Version: 1.0.0
License: MIT
"""

import logging
import re
from pathlib import Path
from typing import List

logger = logging.getLogger()


def find_attachment_files(
    wai_folder: Path,
    max_files: int = 5
) -> List[Path]:
    """Find attachment files in a WAI folder.
    
    Scans the WAI folder for attachment files, excluding the main application
    PDF which follows the pattern {WAI}_{xx}.pdf (e.g., 75179_19.pdf).
    Returns up to max_files attachments, sorted by filename.
    
    Args:
        wai_folder (Path): Path to the WAI number folder.
        max_files (int): Maximum number of attachment files to return.
            Defaults to 5.
    
    Returns:
        List[Path]: List of attachment file paths, sorted by name.
            Empty list if no attachments found.
    
    Example:
        >>> wai_folder = Path("data/Delaney_Wings/Applications/75179")
        >>> attachments = find_attachment_files(wai_folder, max_files=5)
        >>> print(len(attachments))
        5
        >>> print(attachments[0].name)
        75179_19_1.pdf
    
    Note:
        - Excludes files matching pattern {WAI}_{xx}.pdf (main application)
        - Only includes PDF and DOCX files
        - Returns files in sorted order by name
        - Limits results to max_files
    """
    if not wai_folder.exists():
        logger.warning(f"WAI folder does not exist: {wai_folder}")
        return []
    
    # Get WAI number from folder name
    wai_number = wai_folder.name
    
    # Pattern for main application file: {WAI}_{xx}.pdf
    main_app_pattern = re.compile(rf"^{wai_number}_\d+\.pdf$")
    
    # Find all PDF and DOCX files
    attachments = []
    
    # Scan for PDF files
    for pdf_file in wai_folder.glob("*.pdf"):
        # Skip if it matches the main application pattern
        if main_app_pattern.match(pdf_file.name):
            logger.debug(f"Skipping main application file: {pdf_file.name}")
            continue
        attachments.append(pdf_file)
    
    # Scan for DOCX files
    for docx_file in wai_folder.glob("*.docx"):
        attachments.append(docx_file)
    
    # Sort by filename
    attachments.sort(key=lambda x: x.name)
    
    # Limit to max_files
    result = attachments[:max_files]
    
    logger.info(f"Found {len(result)} attachment files in {wai_folder.name} (max: {max_files})")
    
    return result


def get_attachment_output_path(
    source_file: Path,
    output_dir: str,
    scholarship_name: str,
    wai_number: str
) -> Path:
    """Generate output path for redacted attachment text file.
    
    Creates the output directory structure and generates the output filename
    by replacing the source file extension with .txt.
    
    Args:
        source_file (Path): Original attachment file path.
        output_dir (str): Base output directory (e.g., "outputs").
        scholarship_name (str): Name of the scholarship (e.g., "Delaney_Wings").
        wai_number (str): WAI number of the applicant.
    
    Returns:
        Path: Full path for the output .txt file.
    
    Example:
        >>> source = Path("data/Delaney_Wings/Applications/75179/75179_19_1.pdf")
        >>> output = get_attachment_output_path(
        ...     source, "outputs", "Delaney_Wings", "75179"
        ... )
        >>> print(output)
        outputs/Delaney_Wings/75179/attachments/75179_19_1.txt
    
    Note:
        Creates the output directory if it doesn't exist.
    """
    # Create output directory structure: outputs/{scholarship}/{WAI}/attachments/
    output_path = Path(output_dir) / scholarship_name / wai_number / "attachments"
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Generate output filename (replace extension with .txt)
    output_filename = source_file.stem + ".txt"
    
    return output_path / output_filename


def is_attachment_processed(attachment_file: Path, output_dir: str, scholarship_name: str) -> bool:
    """Check if an attachment has already been processed.
    
    Checks if the corresponding .txt file exists in the output directory.
    
    Args:
        attachment_file (Path): Path to the attachment file.
        output_dir (str): Base output directory.
        scholarship_name (str): Name of the scholarship.
    
    Returns:
        bool: True if the attachment has been processed, False otherwise.
    
    Example:
        >>> attachment = Path("data/Delaney_Wings/Applications/75179/75179_19_1.pdf")
        >>> processed = is_attachment_processed(attachment, "outputs", "Delaney_Wings")
        >>> print(processed)
        False
    """
    # Extract WAI number from parent folder
    wai_number = attachment_file.parent.name
    
    # Get expected output path
    output_path = get_attachment_output_path(
        attachment_file, output_dir, scholarship_name, wai_number
    )
    
    return output_path.exists()

# Made with Bob

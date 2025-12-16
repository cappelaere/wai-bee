"""Utility for finding and reading resume/CV text files.

This module provides functions to locate processed resume files (typically the 3rd file)
from the Attachment Agent output and prepare them for academic analysis.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-05
Version: 1.0.0
License: MIT
"""

import logging
from pathlib import Path
from typing import Optional
import os

logger = logging.getLogger()

MARKDOWN_PARSER = os.environ.get("MARKDOWN_PARSER", "false").lower() == "true"


def find_resume_file(
    output_base_dir: Path,
    scholarship_name: str,
    wai_number: str
) -> Optional[Path]:
    """Find resume file (3rd text file) for a WAI folder.
    
    Looks in outputs/{scholarship}/{WAI}/attachments/ for the 3rd .txt file.
    
    Args:
        output_base_dir: Base output directory (e.g., Path("outputs")).
        scholarship_name: Name of the scholarship (e.g., "Delaney_Wings").
        wai_number: WAI application number.
    
    Returns:
        Path object for the resume file, or None if not found.
    
    Example:
        >>> output_dir = Path("outputs")
        >>> resume = find_resume_file(output_dir, "Delaney_Wings", "75179")
        >>> print(resume)
        Path('outputs/Delaney_Wings/75179/attachments/75179_19_3.txt')
    
    Note:
        - Returns None if directory doesn't exist or has fewer than 3 files
        - Processing summary is now .json so no need to exclude
        - Sorts files alphabetically before selecting 3rd file (index 2)
    """
    wai_dir = output_base_dir / scholarship_name / wai_number / "attachments"
    
    if not wai_dir.exists():
        logger.warning(f"Attachments directory not found: {wai_dir}")
        return None
    
    # Find all .txt files (processing summary is now .json)
    txt_files = [
        f for f in wai_dir.glob("*.txt")
    ]
    
    # Sort by filename
    txt_files.sort()
    
    # Check if we have at least 3 files
    if len(txt_files) < 3:
        logger.warning(f"Not enough files in {wai_number}: found {len(txt_files)}, need 3")
        return None
    
    # Return the 3rd file (index 2)
    resume_file = txt_files[2]
    logger.debug(f"Found resume file: {resume_file.name}")
    return resume_file


def read_resume_text(file_path: Path) -> str:
    """Read resume text from file.
    
    Args:
        file_path: Path to the text file.
    
    Returns:
        Content of the file as a string.
    
    Raises:
        FileNotFoundError: If file doesn't exist.
        IOError: If file cannot be read.
    
    Example:
        >>> resume_path = Path("outputs/attachments/Delaney_Wings/75179/75179_19_3.txt")
        >>> content = read_resume_text(resume_path)
        >>> print(len(content))
        2005
    """
    target_path = file_path

    # When MARKDOWN_PARSER is enabled, prefer a corresponding .md file
    if MARKDOWN_PARSER:
        md_path = file_path.with_suffix(".md")
        if md_path.exists():
            logger.info(f"Using Markdown resume file instead of text: {md_path.name}")
            target_path = md_path
        elif not file_path.exists():
            logger.warning(
                f"Markdown parser enabled but neither .md nor .txt resume file found for: {file_path}"
            )

    try:
        with open(target_path, 'r', encoding='utf-8') as f:
            content = f.read()
        logger.debug(f"Read {len(content)} characters from {target_path.name}")
        return content
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        raise IOError(f"Failed to read {file_path}: {str(e)}")


def get_resume_output_path(
    output_base: Path,
    scholarship_name: str,
    wai_number: str
) -> Path:
    """Generate output path for academic analysis JSON.
    
    Args:
        output_base: Base output directory (e.g., Path("outputs")).
        scholarship_name: Name of the scholarship.
        wai_number: WAI application number.
    
    Returns:
        Path object for the output JSON file.
    
    Example:
        >>> output_base = Path("outputs")
        >>> path = get_resume_output_path(output_base, "Delaney_Wings", "75179")
        >>> print(path)
        outputs/Delaney_Wings/75179/academic_analysis.json
    
    Note:
        Does not create the directory - that's done when saving the file.
    """
    return output_base / scholarship_name / wai_number / "academic_analysis.json"


def is_resume_processed(output_path: Path) -> bool:
    """Check if resume has already been processed.
    
    Args:
        output_path: Path to the expected output JSON file.
    
    Returns:
        True if file exists, False otherwise.
    
    Example:
        >>> output_path = Path("outputs/academic/Delaney_Wings/75179/academic_analysis.json")
        >>> if is_resume_processed(output_path):
        ...     print("Already processed")
    """
    exists = output_path.exists()
    if exists:
        logger.debug(f"Resume already processed: {output_path.parent.name}")
    return exists


def get_scholarship_name_from_path(scholarship_folder: Path) -> str:
    """Extract scholarship name from folder path.
    
    Args:
        scholarship_folder: Path to scholarship folder.
    
    Returns:
        Scholarship name (e.g., "Delaney_Wings").
    
    Example:
        >>> folder = Path("data/Delaney_Wings/Applications")
        >>> name = get_scholarship_name_from_path(folder)
        >>> print(name)
        Delaney_Wings
    
    Note:
        Handles both "Applications" subfolder and direct scholarship folder.
    """
    # Get parent directory name (scholarship name)
    if scholarship_folder.name == "Applications":
        return scholarship_folder.parent.name
    return scholarship_folder.name


def validate_resume_file(file_path: Optional[Path]) -> tuple[bool, str]:
    """Validate that resume file exists and has content.
    
    Args:
        file_path: Path to resume file (can be None).
    
    Returns:
        Tuple of (is_valid, error_message).
        If valid, error_message is empty string.
    
    Example:
        >>> resume_path = Path("outputs/attachments/Delaney_Wings/75179/75179_19_3.txt")
        >>> is_valid, error = validate_resume_file(resume_path)
        >>> print(is_valid)
        True
    """
    if file_path is None:
        return False, "Resume file not found"
    
    if not file_path.exists():
        return False, f"Resume file does not exist: {file_path}"
    
    # Check if file has content
    try:
        size = file_path.stat().st_size
        if size == 0:
            return False, f"Resume file is empty: {file_path.name}"
    except Exception as e:
        return False, f"Error checking file: {str(e)}"
    
    return True, ""

# Made with Bob

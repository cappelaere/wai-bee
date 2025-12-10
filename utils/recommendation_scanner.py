"""Utility for finding and reading recommendation text files.

This module provides functions to locate processed recommendation text files
from the Attachment Agent output and prepare them for analysis.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-05
Version: 1.0.0
License: MIT
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger()


def find_recommendation_files(
    output_base_dir: Path,
    scholarship_name: str,
    wai_number: str,
    max_files: int = 2
) -> list[Path]:
    """Find first N recommendation text files for a WAI folder.
    
    Looks in outputs/{scholarship}/{WAI}/attachments/ for .txt files,
    excluding _processing_summary.json.
    
    Args:
        output_base_dir: Base output directory (e.g., Path("outputs")).
        scholarship_name: Name of the scholarship (e.g., "Delaney_Wings").
        wai_number: WAI application number.
        max_files: Maximum number of files to return (default: 2).
    
    Returns:
        List of Path objects for the first N text files found, sorted by name.
    
    Example:
        >>> output_dir = Path("outputs")
        >>> files = find_recommendation_files(output_dir, "Delaney_Wings", "75179", 2)
        >>> print(files)
        [Path('outputs/Delaney_Wings/75179/attachments/75179_19_1.txt'),
         Path('outputs/Delaney_Wings/75179/attachments/75179_19_2.txt')]
    
    Note:
        - Returns empty list if directory doesn't exist
        - Excludes _processing_summary.json
        - Sorts files alphabetically before limiting to max_files
    """
    wai_dir = output_base_dir / scholarship_name / wai_number / "attachments"
    
    if not wai_dir.exists():
        logger.warning(f"Attachments directory not found: {wai_dir}")
        return []
    
    # Find all .txt files (processing summary is now .json)
    txt_files = [
        f for f in wai_dir.glob("*.txt")
    ]
    
    # Sort by filename and limit to max_files
    txt_files.sort()
    result = txt_files[:max_files]
    
    logger.debug(f"Found {len(result)} recommendation files in {wai_number}")
    return result


def read_recommendation_text(file_path: Path) -> str:
    """Read recommendation text from file.
    
    Args:
        file_path: Path to the text file.
    
    Returns:
        Content of the file as a string.
    
    Raises:
        FileNotFoundError: If file doesn't exist.
        IOError: If file cannot be read.
    
    Example:
        >>> file_path = Path("outputs/attachments/Delaney_Wings/75179/75179_19_1.txt")
        >>> text = read_recommendation_text(file_path)
        >>> print(len(text))
        2173
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        logger.debug(f"Read {len(content)} characters from {file_path.name}")
        return content
    except FileNotFoundError:
        logger.error(f"File not found: {file_path}")
        raise
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {str(e)}")
        raise IOError(f"Failed to read {file_path}: {str(e)}")


def get_recommendation_output_path(
    output_base: Path,
    scholarship_name: str,
    wai_number: str
) -> Path:
    """Generate output path for recommendation analysis JSON.
    
    Args:
        output_base: Base output directory (e.g., Path("outputs")).
        scholarship_name: Name of the scholarship.
        wai_number: WAI application number.
    
    Returns:
        Path object for the output JSON file.
    
    Example:
        >>> output_base = Path("outputs")
        >>> path = get_recommendation_output_path(output_base, "Delaney_Wings", "75179")
        >>> print(path)
        outputs/Delaney_Wings/75179/recommendation_analysis.json
    
    Note:
        Does not create the directory - that's done when saving the file.
    """
    return output_base / scholarship_name / wai_number / "recommendation_analysis.json"


def is_recommendation_processed(output_path: Path) -> bool:
    """Check if recommendation has already been processed.
    
    Args:
        output_path: Path to the expected output JSON file.
    
    Returns:
        True if file exists, False otherwise.
    
    Example:
        >>> output_path = Path("outputs/recommendations/Delaney_Wings/75179/recommendation_analysis.json")
        >>> if is_recommendation_processed(output_path):
        ...     print("Already processed")
    """
    exists = output_path.exists()
    if exists:
        logger.debug(f"Recommendation already processed: {output_path.parent.name}")
    return exists


def get_scholarship_name_from_path(scholarship_folder: Path) -> str:
    """Extract scholarship name from folder path.
    
    Args:
        scholarship_folder: Path to scholarship folder.
    
    Returns:
        Scholarship name (last component of path).
    
    Example:
        >>> path = Path("data/Delaney_Wings/Applications")
        >>> name = get_scholarship_name_from_path(path)
        >>> print(name)
        Delaney_Wings
    """
    # Get parent directory name (scholarship name)
    if scholarship_folder.name == "Applications":
        return scholarship_folder.parent.name
    return scholarship_folder.name


def validate_recommendation_files(
    file_paths: list[Path],
    min_files: int = 2
) -> tuple[bool, str]:
    """Validate that we have sufficient recommendation files.
    
    Args:
        file_paths: List of recommendation file paths.
        min_files: Minimum number of files required.
    
    Returns:
        Tuple of (is_valid, error_message).
        If valid, error_message is empty string.
    
    Example:
        >>> files = [Path("file1.txt"), Path("file2.txt")]
        >>> is_valid, error = validate_recommendation_files(files, min_files=2)
        >>> print(is_valid)
        True
    """
    if len(file_paths) < min_files:
        error = f"Insufficient recommendation files: found {len(file_paths)}, need {min_files}"
        return False, error
    
    # Check that all files exist
    for file_path in file_paths:
        if not file_path.exists():
            error = f"Recommendation file not found: {file_path}"
            return False, error
    
    return True, ""


# Made with Bob
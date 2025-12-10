"""Essay file scanner utility.

This module provides functions to locate personal essay files
(files 4 and 5) in the attachments directory.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-06
Version: 1.0.0
License: MIT
"""

import logging
from pathlib import Path


def find_essay_files(
    output_base_dir: Path,
    scholarship_name: str,
    wai_number: str,
    max_files: int = 2
) -> list[Path]:
    """Find personal essay files (files 4 and 5) for a WAI application.
    
    Essays are typically found in files 4 and 5 (indices 3 and 4) of the
    attachments directory. This function returns up to max_files essay files.
    
    Args:
        output_base_dir: Base output directory path (e.g., Path("outputs")).
        scholarship_name: Name of scholarship (e.g., 'Delaney_Wings').
        wai_number: WAI application number.
        max_files: Maximum number of essay files to return (default: 2).
        
    Returns:
        List of Path objects for essay files found (may be 0, 1, or 2 files).
        
    Raises:
        FileNotFoundError: If WAI directory doesn't exist.
        
    Example:
        >>> essays = find_essay_files(Path("outputs"),
        ...                           "Delaney_Wings", "77747")
        >>> print(f"Found {len(essays)} essay files")
        Found 2 essay files
    """
    logger = logging.getLogger()
    
    # Build path to WAI attachments directory in unified structure
    wai_dir = output_base_dir / scholarship_name / wai_number / "attachments"
    
    if not wai_dir.exists():
        raise FileNotFoundError(f"WAI directory not found: {wai_dir}")
    
    # Get all text files, sorted by name
    text_files = sorted(wai_dir.glob("*.txt"))
    
    if not text_files:
        logger.warning(f"No text files found in {wai_dir}")
        return []
    
    # Essay files are at indices 3 and 4 (files 4 and 5)
    # Start index is 3 (4th file), end index is 5 (up to but not including 6th file)
    start_idx = 3
    end_idx = start_idx + max_files
    
    essay_files = text_files[start_idx:end_idx]
    
    if not essay_files:
        logger.warning(f"No essay files found at indices {start_idx}-{end_idx-1} in {wai_dir}")
        return []
    
    logger.info(f"Found {len(essay_files)} essay file(s) for WAI {wai_number}")
    for essay_file in essay_files:
        logger.debug(f"  - {essay_file.name}")
    
    return essay_files


def read_essay_text(essay_file: Path) -> str:
    """Read text content from an essay file.
    
    Args:
        essay_file: Path to essay text file.
        
    Returns:
        Text content of the essay file.
        
    Raises:
        FileNotFoundError: If essay file doesn't exist.
        IOError: If file cannot be read.
        
    Example:
        >>> text = read_essay_text(Path("outputs/attachments/Delaney_Wings/77747/77747_1_4.txt"))
        >>> print(f"Essay length: {len(text)} characters")
        Essay length: 2543 characters
    """
    logger = logging.getLogger()
    
    if not essay_file.exists():
        raise FileNotFoundError(f"Essay file not found: {essay_file}")
    
    try:
        text = essay_file.read_text(encoding='utf-8')
        logger.debug(f"Read {len(text)} characters from {essay_file.name}")
        return text
    except Exception as e:
        logger.error(f"Error reading essay file {essay_file}: {e}")
        raise IOError(f"Failed to read essay file: {e}")


def has_essay_files(
    output_base_dir: Path,
    scholarship_name: str,
    wai_number: str
) -> bool:
    """Check if WAI application has essay files (files 4 and/or 5).
    
    Args:
        output_base_dir: Base output directory path (e.g., Path("outputs")).
        scholarship_name: Name of scholarship.
        wai_number: WAI application number.
        
    Returns:
        True if at least one essay file exists, False otherwise.
        
    Example:
        >>> if has_essay_files(Path("outputs"), "Delaney_Wings", "77747"):
        ...     print("Essays found")
        Essays found
    """
    try:
        essay_files = find_essay_files(output_base_dir, scholarship_name, wai_number)
        return len(essay_files) > 0
    except FileNotFoundError:
        return False

# Made with Bob

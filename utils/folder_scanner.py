"""Utility for scanning scholarship application folders.

This module provides functions for scanning scholarship folders and
identifying WAI number subfolders for processing.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-05
Version: 1.0.0
License: MIT

Functions:
    scan_scholarship_folder: Scan folder and return WAI subfolders.
    get_wai_number: Extract WAI number from folder path.

Example:
    >>> from utils.folder_scanner import scan_scholarship_folder
    >>>
    >>> folders = scan_scholarship_folder(
    ...     "data/Delaney_Wings/Applications",
    ...     max_folders=10
    ... )
    >>> print(f"Found {len(folders)} WAI folders")
"""

import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger()


def scan_scholarship_folder(
    folder_path: str,
    max_folders: Optional[int] = None
) -> List[Path]:
    """Scan scholarship folder and return list of WAI number subfolders.
    
    Scans the specified folder for subdirectories with numeric names
    (WAI numbers), sorts them numerically, and optionally limits the
    number returned.
    
    Args:
        folder_path (str): Path to the scholarship applications folder.
            Example: "data/Delaney_Wings/Applications"
        max_folders (Optional[int]): Maximum number of folders to return.
            If None, returns all folders. Defaults to None.
    
    Returns:
        List[Path]: List of Path objects for WAI number subfolders,
            sorted numerically by WAI number.
    
    Raises:
        FileNotFoundError: If the scholarship folder doesn't exist.
        NotADirectoryError: If the path is not a directory.
    
    Example:
        >>> folders = scan_scholarship_folder(
        ...     "data/Delaney_Wings/Applications",
        ...     max_folders=5
        ... )
        >>> for folder in folders:
        ...     print(folder.name)  # Prints WAI numbers
    """
    base_path = Path(folder_path)
    
    if not base_path.exists():
        raise FileNotFoundError(f"Scholarship folder not found: {folder_path}")
    
    if not base_path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {folder_path}")
    
    # Get all subdirectories that are numeric (WAI numbers)
    wai_folders = []
    for item in base_path.iterdir():
        if item.is_dir() and item.name.isdigit():
            wai_folders.append(item)
    
    # Sort by WAI number (numeric sort)
    wai_folders.sort(key=lambda x: int(x.name))
    
    logger.info(f"Found {len(wai_folders)} WAI folders in {folder_path}")
    
    # Apply limit if specified
    if max_folders is not None and max_folders > 0:
        wai_folders = wai_folders[:max_folders]
        logger.info(f"Limited to first {max_folders} folders")
    
    return wai_folders


def get_wai_number(folder_path: Path) -> str:
    """Extract WAI number from folder path.
    
    Returns the folder name, which represents the WAI number.
    
    Args:
        folder_path (Path): Path object pointing to a WAI folder.
    
    Returns:
        str: WAI number as a string (the folder name).
    
    Example:
        >>> from pathlib import Path
        >>> folder = Path("data/Delaney_Wings/Applications/75179")
        >>> wai = get_wai_number(folder)
        >>> print(wai)
        '75179'
    """
    return folder_path.name


def get_scholarship_name_from_path(scholarship_path: Path) -> str:
    """Extract scholarship name from path.
    
    Returns the scholarship folder name (e.g., "Delaney_Wings" or "Evans_Wings").
    
    Args:
        scholarship_path: Path object pointing to a scholarship folder.
    
    Returns:
        str: Scholarship name (the folder name).
    
    Example:
        >>> from pathlib import Path
        >>> path = Path("data/Delaney_Wings")
        >>> name = get_scholarship_name_from_path(path)
        >>> print(name)
        'Delaney_Wings'
    """
    # Handle both direct scholarship folder and Applications subfolder
    if scholarship_path.name == "Applications":
        return scholarship_path.parent.name
    return scholarship_path.name


# Made with Bob

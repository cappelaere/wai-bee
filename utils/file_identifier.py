"""Utility for identifying application files in WAI folders.

This module provides functions for identifying application files within
WAI number folders and generating output paths for processed results.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-05
Version: 1.0.0
License: MIT

Functions:
    find_application_file: Find the main application file in a WAI folder.
    get_output_json_path: Generate output JSON file path.
    is_already_processed: Check if application has been processed.

Example:
    >>> from pathlib import Path
    >>> from utils.file_identifier import find_application_file
    >>>
    >>> wai_folder = Path("data/Delaney_Wings/Applications/75179")
    >>> app_file = find_application_file(wai_folder)
    >>> if app_file:
    ...     print(f"Found: {app_file.name}")
"""

import logging
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger()


def find_application_file(wai_folder: Path) -> Optional[Path]:
    """Find the application file in a WAI folder.
    
    Identifies the main application file by matching the pattern {WAI}_{xx}.pdf
    or {WAI}_{xx}.docx, where {WAI} is the folder name and {xx} is a number.
    This pattern distinguishes application files from supporting documents
    which have the pattern {WAI}_{xx}_{y}.pdf.
    
    Args:
        wai_folder (Path): Path object pointing to the WAI folder.
    
    Returns:
        Optional[Path]: Path to the application file if found, None otherwise.
    
    Note:
        If multiple application files are found, returns the first one and
        logs a warning.
    
    Example:
        >>> from pathlib import Path
        >>> folder = Path("data/Delaney_Wings/Applications/75179")
        >>> app_file = find_application_file(folder)
        >>> if app_file:
        ...     print(app_file.name)  # e.g., "75179_19.pdf"
    """
    wai_number = wai_folder.name
    
    # Pattern: {WAI}_{xx}.pdf or {WAI}_{xx}.docx (exactly 2 parts separated by underscore)
    pattern = re.compile(rf"^{wai_number}_(\d+)\.(pdf|docx)$", re.IGNORECASE)
    
    application_files = []
    
    for file_path in wai_folder.iterdir():
        if file_path.is_file():
            match = pattern.match(file_path.name)
            if match:
                application_files.append(file_path)
    
    if not application_files:
        logger.warning(f"No application file found in {wai_folder}")
        return None
    
    if len(application_files) > 1:
        logger.warning(
            f"Multiple application files found in {wai_folder}: {[f.name for f in application_files]}. "
            f"Using the first one: {application_files[0].name}"
        )
    
    logger.info(f"Found application file: {application_files[0].name}")
    return application_files[0]


def get_output_json_path(application_file: Path, base_output_dir: str = "outputs") -> Path:
    """Generate the output JSON file path for an application file.
    
    Creates an organized output path structure:
    {base_output_dir}/{scholarship_name}/{WAI}/application_data.json
    
    The function automatically creates the necessary directories if they
    don't exist.
    
    Args:
        application_file (Path): Path to the application file.
        base_output_dir (str): Base output directory. Defaults to "outputs".
    
    Returns:
        Path: Complete path to the output JSON file.
    
    Example:
        >>> from pathlib import Path
        >>> app_file = Path("data/Delaney_Wings/Applications/75179/75179_19.pdf")
        >>> json_path = get_output_json_path(app_file)
        >>> print(json_path)
        outputs/Delaney_Wings/75179/application_data.json
    """
    # Get WAI number from parent folder
    wai_number = application_file.parent.name
    
    # Use consistent filename for application data
    json_filename = "application_data.json"
    
    # Find the scholarship folder (e.g., "Delaney_Wings")
    # Navigate up from application file to find the scholarship name
    scholarship_path = application_file.parent.parent  # Go up from WAI folder to Applications
    scholarship_name = scholarship_path.parent.name  # Get scholarship folder name (e.g., "Delaney_Wings")
    
    # Create output path: outputs/{scholarship_name}/{WAI}/application_data.json
    output_path = Path(base_output_dir) / scholarship_name / wai_number / json_filename
    
    # Create directories if they don't exist
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    return output_path


def is_already_processed(application_file: Path) -> bool:
    """Check if an application has already been processed.
    
    Determines if processing can be skipped by checking for the existence
    of the corresponding JSON output file.
    
    Args:
        application_file (Path): Path to the application file.
    
    Returns:
        bool: True if the corresponding JSON file exists, False otherwise.
    
    Example:
        >>> from pathlib import Path
        >>> app_file = Path("data/Delaney_Wings/Applications/75179/75179_19.pdf")
        >>> if is_already_processed(app_file):
        ...     print("Already processed, skipping")
    """
    json_path = get_output_json_path(application_file)
    return json_path.exists()

# Made with Bob

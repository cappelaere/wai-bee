"""Utility for writing application data to JSON files.

This module provides functions for saving extracted application data
to JSON files with proper formatting and error handling.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-05
Version: 1.0.0
License: MIT

Functions:
    save_application_json: Save application data to JSON file.
    load_application_json: Load application data from JSON file.

Example:
    >>> from pathlib import Path
    >>> from models.application_data import ApplicationData
    >>> from utils.json_writer import save_application_json
    >>>
    >>> data = ApplicationData(
    ...     wai_number="75179",
    ...     name="John Doe",
    ...     city="Boston",
    ...     country="USA",
    ...     source_file="75179_19.pdf"
    ... )
    >>> output_path = Path("outputs/application/Delaney_Wings/75179/75179_19_application.json")
    >>> success = save_application_json(data, output_path)
"""

import json
import logging
from pathlib import Path
from typing import Union

from models.application_data import ApplicationData

logger = logging.getLogger()


def save_application_json(
    data: ApplicationData,
    output_path: Path,
    overwrite: bool = False
) -> bool:
    """Save application data to a JSON file.
    
    Converts the ApplicationData object to a dictionary and saves it as
    a formatted JSON file. Optionally skips if the file already exists.
    
    Args:
        data (ApplicationData): ApplicationData object containing the
            extracted information to save.
        output_path (Path): Path where the JSON file should be saved.
        overwrite (bool): If True, overwrites existing file. If False,
            skips if file exists. Defaults to False.
    
    Returns:
        bool: True if saved successfully, False if skipped or failed.
    
    Note:
        The JSON file is formatted with 2-space indentation and UTF-8
        encoding for readability.
    
    Example:
        >>> from pathlib import Path
        >>> from models.application_data import ApplicationData
        >>>
        >>> data = ApplicationData(
        ...     wai_number="75179",
        ...     name="Jane Smith",
        ...     city="New York",
        ...     country="USA",
        ...     source_file="75179_19.pdf"
        ... )
        >>> path = Path("output.json")
        >>> save_application_json(data, path, overwrite=True)
        True
    """
    try:
        # Check if file already exists
        if output_path.exists() and not overwrite:
            logger.info(f"JSON file already exists, skipping: {output_path.name}")
            return False
        
        # Convert to dict and save as JSON
        data_dict = data.model_dump()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data_dict, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Successfully saved JSON: {output_path.name}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving JSON to {output_path}: {str(e)}")
        return False


def load_application_json(json_path: Path) -> Union[ApplicationData, None]:
    """Load application data from a JSON file.
    
    Reads a JSON file and converts it to an ApplicationData object
    with validation.
    
    Args:
        json_path (Path): Path to the JSON file to load.
    
    Returns:
        Union[ApplicationData, None]: ApplicationData object if successful,
            None if loading or validation fails.
    
    Example:
        >>> from pathlib import Path
        >>> json_path = Path("outputs/application/Delaney_Wings/75179/75179_19_application.json")
        >>> data = load_application_json(json_path)
        >>> if data:
        ...     print(f"Loaded: {data.name}")
    """
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data_dict = json.load(f)
        
        return ApplicationData(**data_dict)
        
    except Exception as e:
        logger.error(f"Error loading JSON from {json_path}: {str(e)}")
        return None

# Made with Bob

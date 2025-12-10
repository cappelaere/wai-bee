"""Utility for parsing PDF and DOCX documents using Docling.

This module provides functions for parsing scholarship application documents
(PDF and DOCX formats) and extracting their text content using the Docling
library.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-05
Version: 1.0.0
License: MIT

Functions:
    parse_document: Parse a document and extract text content.
    get_document_preview: Get a preview of document text.

Example:
    >>> from pathlib import Path
    >>> from utils.document_parser import parse_document
    >>>
    >>> file_path = Path("application.pdf")
    >>> text = parse_document(file_path)
    >>> if text:
    ...     print(f"Extracted {len(text)} characters")
"""

import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger()

# Global converter instance (initialized on first use)
_converter = None


def get_converter():
    """Get or create the global DocumentConverter instance.
    
    Returns:
        DocumentConverter: Singleton instance of the document converter.
    
    Note:
        This function implements lazy initialization to avoid loading
        the converter until it's actually needed.
    """
    global _converter
    if _converter is None:
        from docling.document_converter import DocumentConverter
        logger.info("Initializing DocumentConverter (one-time setup)")
        _converter = DocumentConverter()
    return _converter


def parse_document(file_path: Path, converter=None) -> Optional[str]:
    """Parse a PDF or DOCX document and extract text content.
    
    Uses the Docling library to convert documents to markdown format
    and extract the text content. Supports both PDF and DOCX files.
    
    Args:
        file_path (Path): Path object pointing to the document file.
    
    Returns:
        Optional[str]: Extracted text content as string if successful,
            None if parsing fails or no content is extracted.
    
    Raises:
        ImportError: If Docling library is not installed.
    
    Note:
        The function logs the parsing progress and any errors encountered.
        It returns the markdown representation of the document.
    
    Example:
        >>> from pathlib import Path
        >>> text = parse_document(Path("application.pdf"))
        >>> if text:
        ...     print(f"Document has {len(text)} characters")
    """
    try:
        logger.info(f"Parsing document: {file_path.name}")
        
        # Use provided converter or get the global instance
        if converter is None:
            converter = get_converter()
        
        # Convert the document
        result = converter.convert(str(file_path))
        
        # Extract text from the result
        if result and hasattr(result, 'document'):
            # Get the markdown representation which contains the text
            text_content = result.document.export_to_markdown()
            
            if text_content:
                logger.info(f"Successfully parsed {file_path.name}, extracted {len(text_content)} characters")
                return text_content
            else:
                logger.warning(f"No text content extracted from {file_path.name}")
                return None
        else:
            logger.error(f"Invalid result from document converter for {file_path.name}")
            return None
            
    except ImportError as e:
        logger.error(f"Docling library not installed: {e}")
        raise ImportError(
            "Docling library is required. Install it with: pip install docling"
        )
    except Exception as e:
        logger.error(f"Error parsing document {file_path.name}: {str(e)}")
        return None


def get_document_preview(text: str, max_chars: int = 500) -> str:
    """Get a preview of the document text.
    
    Truncates long text to a specified maximum length and adds ellipsis
    if truncated.
    
    Args:
        text (str): Full document text to preview.
        max_chars (int): Maximum number of characters to return.
            Defaults to 500.
    
    Returns:
        str: Preview of the text, truncated if necessary with "..." appended.
    
    Example:
        >>> long_text = "A" * 1000
        >>> preview = get_document_preview(long_text, max_chars=100)
        >>> len(preview)
        103
        >>> preview.endswith("...")
        True
    """
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "..."

# Made with Bob

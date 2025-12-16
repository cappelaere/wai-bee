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
import os
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger()

# Global converter instances (initialized on first use)
_converter = None          # Docling converter
_md_converter = None       # MarkItDown converter (optional alternate backend)


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
        logger.info("Initializing Docling DocumentConverter (one-time setup)")
        _converter = DocumentConverter()
    return _converter


def get_markitdown_converter():
    """Get or create a global MarkItDown instance.
    
    This provides an alternate backend for document parsing that uses the
    `markitdown` library instead of Docling. It can be used for experiments
    or side-by-side comparisons without changing the existing Docling-based
    behavior.
    """
    global _md_converter
    if _md_converter is None:
        try:
            from markitdown import MarkItDown  # type: ignore
        except ImportError as e:
            logger.error(f"markitdown library not installed: {e}")
            raise ImportError(
                "markitdown library is required for MarkItDown-based parsing. "
                "Install it with: pip install markitdown"
            )
        logger.info("Initializing MarkItDown converter (one-time setup)")
        _md_converter = MarkItDown()
    return _md_converter


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
        
        # Use provided converter or get the global Docling instance
        if converter is None:
            converter = get_converter()
        
        # Convert the document with Docling
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


def parse_document_markdown(file_path: Path, converter=None) -> Optional[str]:
    """Parse a document and extract Markdown using MarkItDown.
    
    This is an alternate implementation of document parsing that uses the
    `markitdown` library instead of Docling. It is intended for experiments
    and for generating Markdown versions of attachments without changing the
    existing Docling-based pipeline.
    
    Args:
        file_path: Path to the document file (PDF, DOCX, etc.).
        converter: Optional MarkItDown instance to reuse. If None, a global
            instance will be created via get_markitdown_converter().
    
    Returns:
        Extracted Markdown text if successful, otherwise None.
    """
    try:
        logger.info(f"[MarkItDown] Parsing document: {file_path.name}")

        # Use provided converter or get the global MarkItDown instance
        if converter is None:
            converter = get_markitdown_converter()

        # MarkItDown API: convert returns an object with text_content
        result = converter.convert(str(file_path))

        text_content = getattr(result, "text_content", None)
        if not text_content and hasattr(result, "markdown"):
            text_content = getattr(result, "markdown")

        if text_content:
            logger.info(
                f"[MarkItDown] Successfully parsed {file_path.name}, "
                f"extracted {len(text_content)} characters"
            )
            return text_content

        logger.warning(f"[MarkItDown] No text content extracted from {file_path.name}")
        return None

    except ImportError:
        # Already logged in get_markitdown_converter
        raise
    except Exception as e:
        logger.error(f"[MarkItDown] Error parsing document {file_path.name}: {str(e)}")
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

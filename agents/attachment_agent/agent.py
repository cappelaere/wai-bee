"""Attachment Agent for processing scholarship application attachments.

This module contains the main AttachmentAgent class that orchestrates the
processing of attachment files. It scans folders, parses documents, removes PII,
and saves redacted text files.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-05
Version: 1.0.0
License: MIT

Example:
    Basic usage of the Attachment Agent::

        from agents.attachment_agent import AttachmentAgent
        
        agent = AttachmentAgent()
        result = agent.process_attachments(
            scholarship_folder="data/Delaney_Wings/Applications",
            max_wai_folders=10,
            max_files_per_folder=5,
            model="ollama/llama3.2:1b"
        )
        
        print(f"Processed: {result.successful}/{result.total}")

Attributes:
    logger: Module-level logger instance for logging operations.
"""

import logging
import time
from pathlib import Path
from typing import Optional

from models.attachment_data import AttachmentData, AttachmentResult
from utils.folder_scanner import scan_scholarship_folder, get_wai_number
from utils.attachment_scanner import (
    find_attachment_files,
    get_attachment_output_path,
    is_attachment_processed
)
from utils.document_parser import parse_document, get_converter
from utils.pii_remover import remove_pii_with_retry
from utils.text_writer import save_redacted_text, create_processing_summary

logger = logging.getLogger()


class AttachmentAgent:
    """Agent for processing scholarship application attachments.
    
    This class orchestrates the entire attachment processing pipeline,
    from scanning folders to removing PII and saving redacted text files.
    
    The agent performs the following steps:
        1. Scans scholarship folder for WAI number subfolders
        2. Identifies attachment files in each folder (excludes main application)
        3. Parses documents using Docling library
        4. Removes PII using LLM
        5. Saves redacted text as .txt files in organized output structure
        6. Tracks timing and performance metrics
    
    Attributes:
        converter: Shared DocumentConverter instance for efficient parsing.
    
    Example:
        >>> agent = AttachmentAgent()
        >>> result = agent.process_attachments(
        ...     scholarship_folder="data/Delaney_Wings/Applications",
        ...     max_files_per_folder=5
        ... )
        >>> print(f"Success rate: {result.successful}/{result.total}")
    """
    
    def __init__(self):
        """Initialize the Attachment Agent.
        
        Creates a new instance of the AttachmentAgent and initializes the
        DocumentConverter for efficient reuse across multiple documents.
        """
        # Initialize the document converter once for reuse
        self.converter = get_converter()
        logger.info("Attachment Agent initialized with DocumentConverter")
    
    def process_single_wai(
        self,
        wai_number: str,
        scholarship_folder: Optional[str] = None,
        output_dir: str = "outputs",
        model: str = "ollama/llama3.2:1b",
        fallback_model: Optional[str] = None,
        max_files: int = 5
    ) -> bool:
        """Process attachments for a single WAI application.
        
        Args:
            wai_number: WAI application number.
            scholarship_folder: Path to scholarship folder. If None, tries to infer.
            output_dir: Base output directory.
            model: Primary LLM model for PII removal.
            fallback_model: Fallback model if primary fails.
            max_files: Maximum number of files to process.
        
        Returns:
            True if successful, False otherwise.
        """
        from pathlib import Path
        
        # Determine scholarship folder if not provided
        if scholarship_folder is None:
            for base in ["data/Delaney_Wings", "data/Evans_Wings"]:
                wai_folder = Path(base) / "Applications" / wai_number
                if wai_folder.exists():
                    scholarship_folder = base
                    break
        
        if scholarship_folder is None:
            logger.error(f"Could not find scholarship folder for WAI {wai_number}")
            return False
        
        scholarship_path = Path(scholarship_folder)
        scholarship_name = scholarship_path.name
        wai_folder = scholarship_path / "Applications" / wai_number
        
        if not wai_folder.exists():
            logger.error(f"WAI folder does not exist: {wai_folder}")
            return False
        
        # Use a dummy result object
        result = AttachmentResult(total=0, successful=0, failed=0)
        
        # Process the WAI folder
        self._process_wai_folder(
            wai_folder=wai_folder,
            wai_number=wai_number,
            max_files=max_files,
            skip_processed=False,
            overwrite=False,
            output_dir=output_dir,
            scholarship_name=scholarship_name,
            model=model,
            fallback_model=fallback_model,
            result=result
        )
        
        return result.successful > 0
    
    def process_attachments(
        self,
        scholarship_folder: str,
        max_wai_folders: Optional[int] = None,
        max_files_per_folder: int = 5,
        skip_processed: bool = True,
        overwrite: bool = False,
        output_dir: str = "outputs",
        model: str = "ollama/llama3.2:1b",
        fallback_model: Optional[str] = None
    ) -> AttachmentResult:
        """Process attachment files from scholarship applications.
        
        Scans the specified scholarship folder for WAI number subfolders,
        processes attachment files (excluding main application PDF), removes
        PII, and saves redacted text files.
        
        Args:
            scholarship_folder (str): Path to the scholarship applications folder.
                Example: "data/Delaney_Wings/Applications"
            max_wai_folders (Optional[int]): Maximum number of WAI folders to
                process. If None, processes all folders. Defaults to None.
            max_files_per_folder (int): Maximum number of attachment files to
                process per WAI folder. Defaults to 5.
            skip_processed (bool): If True, skips attachments that already have
                .txt output files. Defaults to True.
            overwrite (bool): If True, overwrites existing .txt files. Defaults
                to False.
            output_dir (str): Base output directory for .txt files. Defaults to
                "outputs".
            model (str): LLM model to use for PII removal. Format for Ollama:
                "ollama/{model_name}". Defaults to "ollama/llama3.2:1b".
            fallback_model (Optional[str]): Fallback model to use if primary model
                fails. If None, no fallback is used. Defaults to None.
        
        Returns:
            AttachmentResult: Object containing processing statistics including:
                - total: Total attachments attempted
                - successful: Successfully processed count
                - failed: Failed count
                - errors: List of error details
                - total_duration: Total processing time in seconds
                - avg_duration_per_file: Average time per file
        
        Raises:
            FileNotFoundError: If scholarship_folder doesn't exist.
            Exception: For unexpected errors during processing.
        
        Example:
            >>> agent = AttachmentAgent()
            >>> result = agent.process_attachments(
            ...     scholarship_folder="data/Delaney_Wings/Applications",
            ...     max_wai_folders=5,
            ...     max_files_per_folder=5,
            ...     model="ollama/llama3.2:1b",
            ...     fallback_model="ollama/llama3:latest"
            ... )
            >>> print(f"Processed {result.successful} of {result.total} files")
        """
        logger.info(f"Starting to process attachments in: {scholarship_folder}")
        logger.info(f"Model: {model}")
        if fallback_model:
            logger.info(f"Fallback model: {fallback_model}")
        logger.info(f"Max WAI folders: {max_wai_folders or 'unlimited'}")
        logger.info(f"Max files per folder: {max_files_per_folder}")
        logger.info(f"Skip processed: {skip_processed}, Overwrite: {overwrite}")
        
        # Initialize result with start time
        result = AttachmentResult(total=0, successful=0, failed=0)
        result.start_time = time.time()
        
        # Extract scholarship name from path
        scholarship_path = Path(scholarship_folder)
        scholarship_name = scholarship_path.parent.name
        
        try:
            # Scan for WAI folders
            wai_folders = scan_scholarship_folder(scholarship_folder, max_wai_folders)
            
            if len(wai_folders) == 0:
                logger.warning("No WAI folders found to process")
                return result
            
            logger.info(f"Found {len(wai_folders)} WAI folders to process")
            
            # Process each WAI folder
            for idx, wai_folder in enumerate(wai_folders, 1):
                wai_number = get_wai_number(wai_folder)
                logger.info(f"\n[{idx}/{len(wai_folders)}] Processing WAI: {wai_number}")
                
                try:
                    self._process_wai_folder(
                        wai_folder=wai_folder,
                        wai_number=wai_number,
                        max_files=max_files_per_folder,
                        skip_processed=skip_processed,
                        overwrite=overwrite,
                        output_dir=output_dir,
                        scholarship_name=scholarship_name,
                        model=model,
                        fallback_model=fallback_model,
                        result=result
                    )
                except Exception as e:
                    error_msg = f"Unexpected error processing WAI {wai_number}: {str(e)}"
                    logger.error(error_msg)
                    result.add_error(wai_number, error_msg)
            
            # Calculate timing and log summary
            result.end_time = time.time()
            result.calculate_timing()
            
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing complete!")
            logger.info(f"Total files: {result.total}")
            logger.info(f"Successful: {result.successful}")
            logger.info(f"Failed: {result.failed}")
            if result.total_duration:
                logger.info(f"Total duration: {result.total_duration:.2f} seconds")
                logger.info(f"Average per file: {result.avg_duration_per_file:.2f} seconds")
            logger.info(f"{'='*60}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in process_attachments: {str(e)}")
            raise
    
    def _process_wai_folder(
        self,
        wai_folder: Path,
        wai_number: str,
        max_files: int,
        skip_processed: bool,
        overwrite: bool,
        output_dir: str,
        scholarship_name: str,
        model: str,
        fallback_model: Optional[str],
        result: AttachmentResult
    ):
        """Process all attachments in a single WAI folder.
        
        Args:
            wai_folder (Path): Path to the WAI number folder.
            wai_number (str): WAI number of the applicant.
            max_files (int): Maximum number of files to process.
            skip_processed (bool): Whether to skip already processed files.
            overwrite (bool): Whether to overwrite existing files.
            output_dir (str): Base output directory.
            scholarship_name (str): Name of the scholarship.
            model (str): LLM model to use.
            fallback_model (Optional[str]): Fallback model if primary fails.
            result (AttachmentResult): Result object to update.
        """
        # Find attachment files
        attachment_files = find_attachment_files(wai_folder, max_files)
        
        if not attachment_files:
            logger.info(f"No attachment files found in {wai_number}")
            return
        
        logger.info(f"Found {len(attachment_files)} attachment files")
        
        # Track processed attachments for summary
        processed_attachments = []
        
        # Process each attachment
        for file_idx, attachment_file in enumerate(attachment_files, 1):
            logger.info(f"  [{file_idx}/{len(attachment_files)}] Processing: {attachment_file.name}")
            
            try:
                attachment_data = self._process_single_attachment(
                    attachment_file=attachment_file,
                    wai_number=wai_number,
                    skip_processed=skip_processed,
                    overwrite=overwrite,
                    output_dir=output_dir,
                    scholarship_name=scholarship_name,
                    model=model,
                    fallback_model=fallback_model
                )
                
                if attachment_data:
                    result.add_success()
                    result.total += 1
                    processed_attachments.append(attachment_data)
                    logger.info(f"  ✓ Successfully processed {attachment_file.name}")
                else:
                    result.total += 1
                    # Error already logged in _process_single_attachment
                    
            except Exception as e:
                result.total += 1
                result.add_error(
                    wai_number,
                    f"Error processing {attachment_file.name}: {str(e)}",
                    attachment_file.name
                )
                logger.error(f"  ✗ Error processing {attachment_file.name}: {str(e)}")
        
        # Create processing summary for this WAI folder
        if processed_attachments:
            output_path = Path(output_dir) / scholarship_name / wai_number / "attachments"
            create_processing_summary(output_path, wai_number, processed_attachments)
    
    def _process_single_attachment(
        self,
        attachment_file: Path,
        wai_number: str,
        skip_processed: bool,
        overwrite: bool,
        output_dir: str,
        scholarship_name: str,
        model: str,
        fallback_model: Optional[str]
    ) -> Optional[AttachmentData]:
        """Process a single attachment file.
        
        Args:
            attachment_file (Path): Path to the attachment file.
            wai_number (str): WAI number of the applicant.
            skip_processed (bool): Whether to skip if already processed.
            overwrite (bool): Whether to overwrite existing files.
            output_dir (str): Base output directory.
            scholarship_name (str): Name of the scholarship.
            model (str): LLM model to use.
            fallback_model (Optional[str]): Fallback model if primary fails.
        
        Returns:
            Optional[AttachmentData]: Metadata if successful, None if failed.
        """
        errors = []
        source_file_size = 0
        
        # Get source file size
        try:
            source_file_size = attachment_file.stat().st_size
            if source_file_size == 0:
                error_msg = f"Source file is empty (0 bytes): {attachment_file.name}"
                logger.warning(f"  {error_msg}")
                errors.append(error_msg)
        except Exception as e:
            error_msg = f"Failed to get file size: {str(e)}"
            logger.error(f"  {error_msg}")
            errors.append(error_msg)
        
        # Check if already processed
        if skip_processed and is_attachment_processed(attachment_file, output_dir, scholarship_name):
            logger.info(f"  Already processed, skipping: {attachment_file.name}")
            return None
        
        # Parse document
        logger.debug(f"  Parsing document: {attachment_file.name}")
        try:
            document_text = parse_document(attachment_file, self.converter)
            
            if not document_text:
                error_msg = f"Failed to parse document (no text extracted): {attachment_file.name}"
                logger.error(f"  {error_msg}")
                errors.append(error_msg)
                # Create metadata with error
                metadata = AttachmentData(
                    wai_number=wai_number,
                    source_file=attachment_file.name,
                    output_file="",
                    source_file_size=source_file_size,
                    original_length=0,
                    redacted_length=0,
                    pii_types_found=[],
                    has_errors=True,
                    errors=errors
                )
                return metadata
        except Exception as e:
            error_msg = f"Exception during document parsing: {str(e)}"
            logger.error(f"  {error_msg}")
            errors.append(error_msg)
            # Create metadata with error
            metadata = AttachmentData(
                wai_number=wai_number,
                source_file=attachment_file.name,
                output_file="",
                source_file_size=source_file_size,
                original_length=0,
                redacted_length=0,
                pii_types_found=[],
                has_errors=True,
                errors=errors
            )
            return metadata
        
        original_length = len(document_text)
        logger.debug(f"  Extracted {original_length} characters")
        
        # Remove PII
        logger.debug(f"  Removing PII...")
        try:
            redacted_text, pii_types = remove_pii_with_retry(
                document_text,
                model=model,
                fallback_model=fallback_model,
                max_retries=2
            )
            
            if not redacted_text:
                error_msg = "PII removal returned empty text"
                logger.warning(f"  {error_msg}")
                errors.append(error_msg)
        except Exception as e:
            error_msg = f"Exception during PII removal: {str(e)}"
            logger.error(f"  {error_msg}")
            errors.append(error_msg)
            redacted_text = document_text  # Use original text as fallback
            pii_types = []
        
        redacted_length = len(redacted_text)
        
        # Get output path
        output_path = get_attachment_output_path(
            attachment_file, output_dir, scholarship_name, wai_number
        )
        
        # Create metadata
        metadata = AttachmentData(
            wai_number=wai_number,
            source_file=attachment_file.name,
            output_file=output_path.name,
            source_file_size=source_file_size,
            original_length=original_length,
            redacted_length=redacted_length,
            pii_types_found=pii_types,
            has_errors=len(errors) > 0,
            errors=errors
        )
        
        # Save redacted text
        try:
            if save_redacted_text(redacted_text, output_path, metadata, overwrite):
                return metadata
            else:
                # File already exists and overwrite=False
                logger.info(f"  File already exists, skipping save: {output_path.name}")
                return None
        except Exception as e:
            error_msg = f"Failed to save redacted text: {str(e)}"
            logger.error(f"  {error_msg}")
            metadata.errors.append(error_msg)
            metadata.has_errors = True
            return metadata

# Made with Bob

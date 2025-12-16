"""Application Agent for processing scholarship applications.

This module contains the main ApplicationAgent class that orchestrates the
processing of scholarship applications. It scans folders, parses documents,
extracts information using LLM, and saves results as JSON files.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-05
Version: 1.0.0
License: MIT

Example:
    Basic usage of the Application Agent::

        from agents.application_agent import ApplicationAgent
        
        agent = ApplicationAgent()
        result = agent.process_applications(
            scholarship_folder="data/Delaney_Wings/Applications",
            max_applications=10,
            model="ollama/llama3.2:1b"
        )
        
        print(f"Processed: {result.successful}/{result.total}")

Attributes:
    logger: Module-level logger instance for logging operations.
"""

import logging
import os
import time
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from models.application_data import ApplicationData, ProcessingResult
from utils.folder_scanner import scan_scholarship_folder, get_wai_number
from utils.file_identifier import find_application_file

MARKDOWN_PARSER = os.environ.get('MARKDOWN_PARSER', 'false').lower() == 'true'

from utils.document_parser import parse_document, get_converter
from utils.document_parser import parse_document_markdown, get_markitdown_converter

from .llm_service import LLMService
from .validation_service import ValidationService
from .file_service import FileService

logger = logging.getLogger()

logger.info(f"MARKDOWN_PARSER: {MARKDOWN_PARSER}")
class ApplicationAgent:
    """Agent for processing scholarship applications.
    
    This class orchestrates the entire scholarship application processing pipeline,
    from scanning folders to extracting information and saving results.
    
    The agent performs the following steps:
        1. Scans scholarship folder for WAI number subfolders
        2. Identifies application files in each folder (pattern: {WAI}_{xx}.pdf)
        3. Parses documents using Docling library
        4. Extracts applicant information (name, city, country) using LLM
        5. Saves extracted data as JSON files in organized output structure
        6. Tracks timing and performance metrics
    
    Attributes:
        None (stateless agent)
    
    Example:
        >>> agent = ApplicationAgent()
        >>> result = agent.process_applications(
        ...     scholarship_folder="data/Delaney_Wings/Applications",
        ...     model="ollama/llama3.2:1b"
        ... )
        >>> print(f"Success rate: {result.successful}/{result.total}")
    """
    
    def __init__(self):
        """Initialize the Application Agent.
        
        Creates a new instance of the ApplicationAgent and initializes the
        DocumentConverter for efficient reuse across multiple documents.
        """
        # Initialize the document converter once for reuse
        if MARKDOWN_PARSER:
            self.md_converter = get_markitdown_converter()
        else:
            self.converter = get_converter()
        logger.info("Application Agent initialized with DocumentConverter")
    
    def analyze_application(
        self,
        wai_number: str,
        scholarship_folder: Optional[str] = None,
        output_dir: str = "outputs",
        model: Optional[str] = None,
        fallback_model: Optional[str] = None,
        max_retries: Optional[int] = None
    ) -> Optional[ApplicationData]:
        """Analyze a single application.
        
        Args:
            wai_number: WAI application number.
            scholarship_folder: Path to scholarship folder. If None, uses default pattern.
            output_dir: Base output directory.
            model: Primary LLM model to use. If None, uses PRIMARY_MODEL from .env.
            fallback_model: Fallback model if primary fails. If None, uses FALLBACK_MODEL from .env.
            max_retries: Maximum retry attempts. If None, uses MAX_RETRIES from .env.
        
        Returns:
            ApplicationData if successful, None otherwise.
        """
        from pathlib import Path
        
        # Load defaults from environment variables if not provided
        if model is None:
            model = os.getenv('PRIMARY_MODEL', 'ollama/llama3.2:3b')
        if fallback_model is None:
            fallback_model = os.getenv('FALLBACK_MODEL', 'ollama/llama3:latest')
        if max_retries is None:
            max_retries = int(os.getenv('MAX_RETRIES', '3'))
        
        # Determine scholarship folder if not provided
        if scholarship_folder is None:
            # Try to find the WAI folder in common locations
            for base in ["data/Delaney_Wings/Applications", "data/Evans_Wings/Applications"]:
                wai_folder = Path(base) / wai_number
                if wai_folder.exists():
                    scholarship_folder = base
                    break
        
        if scholarship_folder is None:
            logger.error(f"Could not find WAI folder for {wai_number}")
            return None
        
        # Handle both direct scholarship folder and Applications subfolder
        scholarship_path = Path(scholarship_folder)
        if scholarship_path.name != "Applications":
            # If given scholarship folder (e.g., data/Delaney_Wings), append Applications
            wai_folder = scholarship_path / "Applications" / wai_number
        else:
            # If given Applications folder directly
            wai_folder = scholarship_path / wai_number
            
        if not wai_folder.exists():
            logger.error(f"WAI folder does not exist: {wai_folder}")
            return None
        
        # Use a dummy result object to track success/failure
        from models.application_data import ProcessingResult
        result = ProcessingResult(total=1, successful=0, failed=0)
        
        # Process the single application
        self._process_single_application(
            wai_folder=wai_folder,
            wai_number=wai_number,
            skip_processed=False,
            overwrite=False,
            output_dir=output_dir,
            model=model,
            fallback_model=fallback_model,
            max_retries=max_retries,
            result=result,
            scholarship_folder=scholarship_path
        )
        
        if result.successful > 0:
            # Load and return the saved data
            app_file = find_application_file(wai_folder)
            if app_file:
                _, _, output_path, _ = FileService.check_processing_status(app_file, output_dir, False)
                if output_path and output_path.exists():
                    return FileService.load_existing_extraction(output_path)
        
        return None
    
    def process_applications(
        self,
        scholarship_folder: str,
        max_applications: Optional[int] = None,
        skip_processed: Optional[bool] = None,
        overwrite: Optional[bool] = None,
        output_dir: str = "outputs",
        model: Optional[str] = None,
        fallback_model: Optional[str] = None,
        max_retries: Optional[int] = None
    ) -> ProcessingResult:
        """Process scholarship applications in a folder.
        
        Scans the specified scholarship folder for WAI number subfolders,
        processes each application file, extracts information using LLM,
        and saves results as JSON files.
        
        Args:
            scholarship_folder (str): Path to the scholarship applications folder.
                Example: "data/Delaney_Wings/Applications"
            max_applications (Optional[int]): Maximum number of applications to
                process. If None, processes all applications. Defaults to None.
            skip_processed (bool): If True, skips applications that already have
                JSON output files. Defaults to True.
            overwrite (bool): If True, overwrites existing JSON files. Defaults
                to False.
            output_dir (str): Base output directory for JSON files. Defaults to
                "outputs".
            model (str): LLM model to use for extraction. Format for Ollama:
                "ollama/{model_name}". Defaults to "ollama/llama3.2:1b".
                Examples: "ollama/llama3.2:3b", "gpt-4o-mini"
            fallback_model (Optional[str]): Fallback model to use if primary model
                fails after retries. If None, no fallback is used. Defaults to None.
                Example: "ollama/llama3:latest"
            max_retries (int): Maximum number of retry attempts for extraction.
                Defaults to 3.
        
        Returns:
            ProcessingResult: Object containing processing statistics including:
                - total: Total applications attempted
                - successful: Successfully processed count
                - failed: Failed count
                - errors: List of error details
                - total_duration: Total processing time in seconds
                - avg_duration_per_app: Average time per application
        
        Raises:
            FileNotFoundError: If scholarship_folder doesn't exist.
            Exception: For unexpected errors during processing.
        
        Example:
            >>> agent = ApplicationAgent()
            >>> result = agent.process_applications(
            ...     scholarship_folder="data/Delaney_Wings/Applications",
            ...     max_applications=5,
            ...     model="ollama/llama3.2:1b"
            ... )
            >>> print(f"Processed {result.successful} applications")
        """
        # Load defaults from environment variables if not provided
        if model is None:
            model = os.getenv('PRIMARY_MODEL', 'ollama/llama3.2:3b')
        if fallback_model is None:
            fallback_model = os.getenv('FALLBACK_MODEL', 'ollama/llama3:latest')
        if max_retries is None:
            max_retries = int(os.getenv('MAX_RETRIES', '3'))
        if skip_processed is None:
            skip_processed = os.getenv('SKIP_PROCESSED', 'true').lower() == 'true'
        if overwrite is None:
            overwrite = os.getenv('OVERWRITE_EXISTING', 'false').lower() == 'true'
        
        logger.info(f"Starting to process applications in: {scholarship_folder}")
        logger.info(f"Model: {model}")
        if fallback_model:
            logger.info(f"Fallback model: {fallback_model}")
        logger.info(f"Max retries: {max_retries}")
        logger.info(f"Max applications: {max_applications or 'unlimited'}")
        logger.info(f"Skip processed: {skip_processed}, Overwrite: {overwrite}")
        
        # Initialize result with start time
        result = ProcessingResult(total=0, successful=0, failed=0)
        result.start_time = time.time()
        
        try:
            # Scan for WAI folders
            wai_folders = scan_scholarship_folder(scholarship_folder, max_applications)
            result.total = len(wai_folders)
            
            if result.total == 0:
                logger.warning("No WAI folders found to process")
                return result
            
            # Process each folder
            for idx, wai_folder in enumerate(wai_folders, 1):
                wai_number = get_wai_number(wai_folder)
                logger.info(f"\n[{idx}/{result.total}] Processing WAI: {wai_number}")
                
                try:
                    self._process_single_application(
                        wai_folder=wai_folder,
                        wai_number=wai_number,
                        skip_processed=skip_processed,
                        overwrite=overwrite,
                        output_dir=output_dir,
                        model=model,
                        fallback_model=fallback_model,
                        max_retries=max_retries,
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
            logger.info(f"Total: {result.total}")
            logger.info(f"Successful: {result.successful}")
            logger.info(f"Failed: {result.failed}")
            if result.total_duration:
                logger.info(f"Total duration: {result.total_duration:.2f} seconds")
                logger.info(f"Average per application: {result.avg_duration_per_app:.2f} seconds")
            logger.info(f"{'='*60}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in process_applications: {str(e)}")
            raise
    
    def _process_single_application(
        self,
        wai_folder: Path,
        wai_number: str,
        skip_processed: bool,
        overwrite: bool,
        output_dir: str,
        model: str,
        fallback_model: Optional[str],
        max_retries: int,
        result: ProcessingResult,
        scholarship_folder: Optional[Path] = None
    ):
        """Process a single scholarship application.
        
        PROCESSING FLOW:
        1. Find application PDF file
        2. Check skip logic (both extraction and analysis files)
        3. Extract data from PDF (or load existing)
        4. Score the application
        5. Save analysis JSON
        """
        
        # ========== STEP 1: Find Application File ==========
        app_file = find_application_file(wai_folder)
        if not app_file:
            result.add_error(wai_number, "Application file not found")
            return
        
        # ========== STEP 2: Check Skip Logic ==========
        extraction_exists, analysis_exists, output_path, analysis_path = FileService.check_processing_status(
            app_file, output_dir, skip_processed
        )
        
        if not output_path or not analysis_path:
            result.add_error(wai_number, "Failed to determine output paths")
            return
        
        # Case 1: Both files exist - skip everything
        if skip_processed and extraction_exists and analysis_exists:
            logger.info(f"Already processed (extraction and analysis), skipping: {app_file.name}")
            result.add_success()
            return
        
        # Case 2: Only extraction exists - load it and skip to scoring
        extracted_data = None
        if skip_processed and extraction_exists and not analysis_exists:
            logger.info(f"Extraction exists but analysis missing, will score application: {app_file.name}")
            extracted_data = FileService.load_existing_extraction(output_path)
        
        # Case 3: Nothing exists or not skipping - do full extraction
        if extracted_data is None:
            # ========== STEP 3: Extract Application Data ==========
            logger.info(f"Parsing document: {app_file.name}")
            if MARKDOWN_PARSER:
                document_text = parse_document_markdown(app_file, self.md_converter)
            else:
                document_text = parse_document(app_file, self.converter)
            if not document_text:
                result.add_error(
                    wai_number,
                    "Failed to parse document",
                    app_file.name
                )
                return
            
            # Extract information using LLM with retry logic
            logger.info("Extracting applicant information...")
            extracted_data = LLMService.extract_information_with_retry(
                document_text, wai_number, app_file.name, model,
                fallback_model, max_retries
            )
            if not extracted_data:
                result.add_error(
                    wai_number,
                    "Failed to extract information from document",
                    app_file.name
                )
                return
            
            # ========== STEP 3a: Check Attachment Files ==========
            logger.info("Checking for required attachment files...")
            attachment_file_details = ValidationService.check_attachment_files(wai_folder, app_file.name)
            
            # ========== STEP 3b: Validate Extracted Data ==========
            validation_passed = ValidationService.validate_extracted_data(extracted_data, attachment_file_details)
            
            if not validation_passed:
                # Save extraction JSON with errors
                if not FileService.save_extraction(extracted_data, output_path, overwrite):
                    logger.error("Failed to save extraction JSON with validation errors")
                
                # Add to result errors and raise exception to stop workflow
                error_msg = f"Validation failed: {'; '.join(extracted_data.validation_errors)}"
                result.add_error(wai_number, error_msg, app_file.name)
                logger.error(f"❌ Stopping processing for {wai_number} due to validation errors")
                raise ValueError(error_msg)
            
            # ========== STEP 3c: Save Extraction JSON ==========
            if not FileService.save_extraction(extracted_data, output_path, overwrite):
                result.add_error(
                    wai_number,
                    "Failed to save extraction JSON file",
                    app_file.name
                )
                return
        
        # Score the application (only if we have extracted data)
        if extracted_data is None:
            logger.error(f"No extracted data available for scoring {wai_number}")
            result.add_error(wai_number, "No extracted data available", app_file.name)
            return
        
        logger.info("Scoring application completeness and validity...")
        output_dir_path = Path(output_dir)
        
        # Use the scholarship_folder parameter if provided, otherwise derive it
        if scholarship_folder is None:
            scholarship_folder = Path(wai_folder).parent.parent
        
        # Use a larger model for scoring if the extraction model is too small
        scoring_model = model
        if "1b" in model.lower():
            scoring_model = model.replace("1b", "3b")
            logger.info(f"Using larger model for scoring: {scoring_model}")
        
        analysis = LLMService.score_application(
            app_data=extracted_data,
            scholarship_folder=scholarship_folder,
            wai_number=wai_number,
            output_dir=output_dir_path,
            model=scoring_model,
            max_retries=max_retries
        )
        
        if analysis:
            # Save analysis JSON
            if FileService.save_analysis(analysis, analysis_path):
                result.add_success()
                logger.info(f"✓ Successfully processed and scored {wai_number}")
            else:
                result.add_error(wai_number, "Failed to save analysis", app_file.name)
        else:
            logger.warning(f"Scoring failed for {wai_number}, but extraction succeeded")
            result.add_success()  # Still count as success since extraction worked
    

# Made with Bob

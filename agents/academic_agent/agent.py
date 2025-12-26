"""Academic Agent for analyzing academic profiles from resumes.

This module contains the main AcademicAgent class that orchestrates the
analysis of resume/CV files using LLM and generates structured academic
evaluation reports with scores and detailed analysis.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-05
Version: 1.0.0
License: MIT

Example:
    Basic usage of the Academic Agent::

        from agents.academic_agent import AcademicAgent
        
        agent = AcademicAgent()
        result = agent.process_resumes(
            scholarship_folder="data/Delaney_Wings",
            max_wai_folders=10,
            model="ollama/llama3.2:3b"
        )
        
        print(f"Processed: {result.successful}/{result.total}")

Attributes:
    logger: Module-level logger instance for logging operations.
"""

import json
import logging, traceback
import os
import time
from pathlib import Path
from typing import Optional

# Suppress LiteLLM's verbose logging
os.environ["LITELLM_LOG"] = "ERROR"
import litellm
litellm.suppress_debug_info = True

from litellm import completion

from models.academic_data import (
    AcademicData,
    ProcessingResult,
    ProcessingError
)
from utils.folder_scanner import scan_scholarship_folder, get_wai_number
from utils.resume_scanner import (
    find_resume_file,
    read_resume_text,
    get_resume_output_path,
    is_resume_processed,
    get_scholarship_name_from_path,
    validate_resume_file
)
from utils.criteria_loader import load_criteria
from utils.schema_validator import (
    load_schema,
    validate_and_fix_iterative,
    extract_json_from_text
)
from .prompts import SYSTEM_PROMPT, build_analysis_prompt, build_retry_prompt

logger = logging.getLogger()


class AcademicAgent:
    """Agent for analyzing academic profiles using LLM.
    
    This agent processes resume/CV files from scholarship applications,
    analyzes them using LLM with scholarship-specific criteria, and generates
    structured JSON output with scores and detailed academic analysis.
    
    Attributes:
        schema: JSON schema for output validation.
        schema_path: Path to the schema file.
    
    Example:
        >>> agent = AcademicAgent()
        >>> result = agent.process_resumes(
        ...     scholarship_folder="data/Delaney_Wings",
        ...     model="ollama/llama3.2:3b",
        ...     max_wai_folders=10
        ... )
        >>> print(f"Success rate: {result.successful}/{result.total}")
    """
    
    def __init__(self, schema_path: Optional[Path] = None):
        """Initialize the Academic Agent.
        
        Args:
            schema_path: Path to JSON schema file. If None, uses default path.
        """
        self.schema_path = schema_path or Path("schemas/resume_agent_schema.json")
        self.schema = load_schema(self.schema_path)
        logger.info("Academic Agent initialized")
    
    def analyze_academic_profile(
        self,
        wai_number: str,
        scholarship_folder: Optional[str] = None,
        model: str = "ollama/llama3.2:3b",
        fallback_model: str = "ollama/llama3:latest",
        max_retries: int = 3
    ) -> Optional['AcademicData']:
        """Analyze academic profile for a single WAI application.
        
        Args:
            wai_number: WAI application number.
            scholarship_folder: Path to scholarship folder (e.g., "data/Delaney_Wings").
            model: Primary LLM model to use.
            fallback_model: Fallback model if primary fails.
            max_retries: Maximum retry attempts.
        
        Returns:
            AcademicData if successful, None otherwise.
        """
        from pathlib import Path
        from utils.folder_scanner import get_scholarship_name_from_path
        from utils.criteria_loader import load_criteria, get_criteria_path
        
        # Determine scholarship folder and name
        if scholarship_folder is None:
            # Try to infer from common patterns
            for base in ["data/Delaney_Wings", "data/Evans_Wings"]:
                if Path(base).exists():
                    scholarship_folder = base
                    break
        
        if scholarship_folder is None:
            logger.error("Could not determine scholarship folder")
            return None
        
        scholarship_path = Path(scholarship_folder)
        scholarship_name = get_scholarship_name_from_path(scholarship_path)
        
        # Load criteria
        criteria = load_criteria(scholarship_path)
        criteria_path = get_criteria_path(scholarship_path)
        
        # Process single WAI
        return self._process_single_wai(
            wai_folder=scholarship_path / "Applications" / wai_number,
            wai_number=wai_number,
            scholarship_name=scholarship_name,
            criteria=criteria,
            criteria_path=str(criteria_path),
            model=model,
            fallback_model=fallback_model,
            max_retries=max_retries
        )
    
    def process_resumes(
        self,
        scholarship_folder: str,
        model: str = "ollama/llama3.2:3b",
        fallback_model: str = "ollama/llama3:latest",
        max_wai_folders: Optional[int] = 10,
        max_retries: int = 3,
        skip_processed: bool = True,
        overwrite: bool = False
    ) -> ProcessingResult:
        """Process resumes for all WAI folders in scholarship.
        
        Args:
            scholarship_folder: Path to scholarship folder (e.g., "data/Delaney_Wings").
            model: Primary LLM model to use (default: "ollama/llama3.2:3b").
            fallback_model: Fallback model if primary fails (default: "ollama/llama3:latest").
            max_wai_folders: Maximum number of WAI folders to process (default: 10).
            max_retries: Maximum retry attempts per WAI (default: 3).
            skip_processed: Skip already processed WAI folders (default: True).
            overwrite: Overwrite existing output files (default: False).
        
        Returns:
            ProcessingResult with statistics and errors.
        
        Example:
            >>> agent = AcademicAgent()
            >>> result = agent.process_resumes(
            ...     scholarship_folder="data/Delaney_Wings/Applications",
            ...     max_wai_folders=5
            ... )
            >>> print(f"Processed {result.successful} resumes")
        """
        start_time = time.time()
        scholarship_path = Path(scholarship_folder)
        scholarship_name = get_scholarship_name_from_path(scholarship_path)
        
        # Load criteria once for all WAI folders
        criteria = load_criteria(scholarship_path, "academic")
        
        # Handle both "Applications" subfolder and direct scholarship folder
        if scholarship_path.name == "Applications":
            criteria_folder = scholarship_path.parent
        else:
            criteria_folder = scholarship_path
        criteria_path = str(criteria_folder / "criteria" / "academic_criteria.txt")
        
        logger.info(f"Processing academic profiles for: {scholarship_name}")
        logger.info(f"Using criteria: {criteria_path}")
        
        # Scan for WAI folders
        wai_folders = scan_scholarship_folder(scholarship_path, max_folders=max_wai_folders)
        logger.info(f"Found {len(wai_folders)} WAI folders to process")
        
        # Process each WAI folder
        successful = 0
        failed = 0
        skipped = 0
        errors = []
        
        for idx, wai_folder in enumerate(wai_folders, 1):
            wai_number = get_wai_number(wai_folder)
            logger.info(f"\nProcessing {idx}/{len(wai_folders)}: WAI {wai_number}")
            
            try:
                # Check if already processed
                output_path = get_resume_output_path(
                    Path("outputs"),
                    scholarship_name,
                    wai_number
                )
                
                if skip_processed and not overwrite and is_resume_processed(output_path):
                    logger.info(f"  ✓ Already processed, skipping")
                    skipped += 1
                    continue
                
                # Process this WAI
                result = self._process_single_wai(
                    wai_folder=wai_folder,
                    wai_number=wai_number,
                    scholarship_name=scholarship_name,
                    criteria=criteria,
                    criteria_path=criteria_path,
                    model=model,
                    fallback_model=fallback_model,
                    max_retries=max_retries
                )
                
                if result:
                    successful += 1
                    logger.info(f"  ✓ Successfully processed {wai_number}")
                else:
                    failed += 1
                    logger.warning(f"  ✗ Failed to process {wai_number}")
                    
            except Exception as e:
                failed += 1
                logger.exception(f"  ✗ Unexpected error processing {wai_number}")
                errors.append(ProcessingError(
                    wai_number=wai_number,
                    error_type=type(e).__name__,
                    error_message=str(e)
                ))
        
        # Calculate statistics
        duration = time.time() - start_time
        total = len(wai_folders)
        
        result = ProcessingResult(
            total=total,
            successful=successful,
            failed=failed,
            skipped=skipped,
            errors=errors,
            duration=duration
        )
        
        # Log summary
        logger.info("\n" + "="*60)
        logger.info("Processing complete!")
        logger.info(f"Total WAI folders: {total}")
        logger.info(f"Successful: {successful}")
        logger.info(f"Failed: {failed}")
        logger.info(f"Skipped: {skipped}")
        logger.info(f"Total duration: {duration:.2f} seconds")
        logger.info(f"Average per WAI: {result.average_per_wai:.2f} seconds")
        logger.info("="*60)
        
        return result
    
    def _process_single_wai(
        self,
        wai_folder: Path,
        wai_number: str,
        scholarship_name: str,
        criteria: str,
        criteria_path: str,
        model: str,
        fallback_model: str,
        max_retries: int
    ) -> Optional[AcademicData]:
        """Process resume for a single WAI folder.
        
        Args:
            wai_folder: Path to WAI folder.
            wai_number: WAI application number.
            scholarship_name: Name of the scholarship.
            criteria: Evaluation criteria text.
            criteria_path: Path to criteria file.
            model: Primary LLM model.
            fallback_model: Fallback LLM model.
            max_retries: Maximum retry attempts.
        
        Returns:
            AcademicData if successful, None otherwise.
        """
        try:
            # Find resume file (3rd file) in unified output structure
            output_base = Path("outputs")
            resume_file = find_resume_file(
                output_base,
                scholarship_name,
                wai_number
            )
            
            # Validate file
            is_valid, error_msg = validate_resume_file(resume_file)
            if not is_valid:
                logger.warning(f"  {error_msg}")
                return None
            
            logger.info(f"  Found resume file: {resume_file.name}")
            
            # Read resume text
            resume_text = read_resume_text(resume_file)
            
            # Try analysis with retries
            for attempt in range(1, max_retries + 1):
                try:
                    current_model = model if attempt == 1 else fallback_model
                    logger.info(f"  Analysis attempt {attempt}/{max_retries} with {current_model}")
                    
                    # Analyze with LLM
                    response_text = self._analyze_with_llm(resume_text, criteria, current_model)
                    
                    # Extract and validate JSON
                    json_text = extract_json_from_text(response_text)
                    is_valid, fixed_data, error_msg = validate_and_fix_iterative(
                        json_text,
                        self.schema,
                        max_attempts=3
                    )
                    
                    if is_valid and fixed_data:
                        #logger.info(f"  ✓ Validation successful")
                        break
                    else:
                        logger.warning(f"  Validation failed: {error_msg}")
                        if attempt == max_retries:
                            logger.error(f"  Max retries reached, using default values")
                            return None
                        
                except Exception:
                    logger.exception(f"  Attempt {attempt} failed for {wai_number}")
                    if attempt == max_retries:
                        return None
            
            # Create AcademicData object
            scores = fixed_data.get("scores", {})
            logger.info(f"Academic Scores: {scores}")
           
            # Calculate from component scores
            overall = (
                scores.get('academic_performance_score', 0) +
                scores.get('academic_relevance_score', 0) +
                scores.get('academic_readiness_score', 0)
            )
            scores['overall_score'] = int(overall)
            logger.debug(f"Calculated academic overall_score: {scores['overall_score']}")
            
            academic_data = AcademicData(
                wai_number=wai_number,
                summary=fixed_data.get("summary", "Unknown"),
                profile_features=fixed_data.get("profile_features", {}),
                scores=scores,
                score_breakdown=fixed_data.get("score_breakdown", {}),
                source_file=resume_file.name,
                model_used=current_model,
                criteria_used=criteria_path,
            )
            
            # Save to JSON
            output_path = get_resume_output_path(
                Path("outputs"),
                scholarship_name,
                wai_number
            )
            self._save_json(academic_data, output_path)
            
            return academic_data

        except Exception:
            logger.exception(f"  Error processing academic agent: {wai_number}")
            return None
    
    def _analyze_with_llm(
        self,
        resume_text: str,
        criteria: str,
        model: str
    ) -> str:
        """Call LLM to analyze resume.
        
        Args:
            resume_text: Content of the resume/CV.
            criteria: Evaluation criteria.
            model: LLM model to use.
        
        Returns:
            LLM response as string.
        
        Raises:
            Exception: If LLM call fails.
        """
        # Build prompt
        prompt = build_analysis_prompt(resume_text, criteria)
        
        # Call LLM
        response = completion(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=4000
        )
        
        # Extract content from response
        content = response.choices[0].message.content
        return content if content else ""
    
    def _save_json(self, data: AcademicData, output_path: Path) -> bool:
        """Save academic data to JSON file.
        
        Args:
            data: AcademicData object.
            output_path: Path where JSON should be saved.
        
        Returns:
            True if successful, False otherwise.
        """
        try:
            # Ensure directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert to dict and save
            data_dict = data.model_dump(mode='json')
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data_dict, f, indent=2, ensure_ascii=False)
            
            logger.debug(f"  Saved analysis to: {output_path}")
            return True
            
        except Exception:
            logger.exception("  Error saving JSON")
            return False


# Made with Bob
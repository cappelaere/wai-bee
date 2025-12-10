"""Recommendation Agent for analyzing recommendation letters.

This module contains the main RecommendationAgent class that orchestrates the
analysis of recommendation letters using LLM and generates structured evaluation
reports with scores and detailed analysis.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-05
Version: 1.0.0
License: MIT

Example:
    Basic usage of the Recommendation Agent::

        from agents.recommendation_agent import RecommendationAgent
        
        agent = RecommendationAgent()
        result = agent.process_recommendations(
            scholarship_folder="data/Delaney_Wings",
            max_wai_folders=10,
            model="ollama/llama3.2:1b"
        )
        
        print(f"Processed: {result.successful}/{result.total}")

Attributes:
    logger: Module-level logger instance for logging operations.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

# Suppress LiteLLM's verbose logging
os.environ["LITELLM_LOG"] = "ERROR"
import litellm
litellm.suppress_debug_info = True

from litellm import completion

from models.recommendation_data import (
    RecommendationData,
    ProcessingResult,
    ProcessingError
)
from utils.folder_scanner import scan_scholarship_folder, get_wai_number
from utils.recommendation_scanner import (
    find_recommendation_files,
    read_recommendation_text,
    get_recommendation_output_path,
    is_recommendation_processed,
    get_scholarship_name_from_path,
    validate_recommendation_files
)
from utils.criteria_loader import load_criteria, get_criteria_path
from utils.schema_validator import (
    load_schema,
    validate_and_fix_iterative,
    extract_json_from_text
)
from .prompts import SYSTEM_PROMPT, build_analysis_prompt, build_retry_prompt

logger = logging.getLogger()


class RecommendationAgent:
    """Agent for analyzing recommendation letters using LLM.
    
    This agent processes recommendation letters from scholarship applications,
    analyzes them using LLM with scholarship-specific criteria, and generates
    structured JSON output with scores and detailed analysis.
    
    Attributes:
        schema: JSON schema for output validation.
        schema_path: Path to the schema file.
    
    Example:
        >>> agent = RecommendationAgent()
        >>> result = agent.process_recommendations(
        ...     scholarship_folder="data/Delaney_Wings",
        ...     model="ollama/llama3.2:3b",
        ...     max_wai_folders=10
        ... )
        >>> print(f"Success rate: {result.successful}/{result.total}")
    """
    
    def __init__(self, schema_path: Optional[Path] = None):
        """Initialize the Recommendation Agent.
        
        Args:
            schema_path: Path to JSON schema file. If None, uses default path.
        """
        self.schema_path = schema_path or Path("schemas/recommendation_agent_schema.json")
        self.schema = load_schema(self.schema_path)
        logger.info("Recommendation Agent initialized")
    
    def analyze_recommendations(
        self,
        wai_number: str,
        scholarship_folder: Optional[str] = None,
        model: str = "ollama/llama3.2:3b",
        fallback_model: str = "ollama/llama3:latest",
        max_retries: int = 3
    ) -> Optional[RecommendationData]:
        """Analyze recommendations for a single WAI application.
        
        Args:
            wai_number: WAI application number.
            scholarship_folder: Path to scholarship folder (e.g., "data/Delaney_Wings").
            model: Primary LLM model to use.
            fallback_model: Fallback model if primary fails.
            max_retries: Maximum retry attempts.
        
        Returns:
            RecommendationData if successful, None otherwise.
        """
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
            min_files=2,
            max_retries=max_retries
        )
    
    def process_recommendations(
        self,
        scholarship_folder: str,
        model: str = "ollama/llama3.2:3b",
        fallback_model: str = "ollama/llama3:latest",
        max_wai_folders: Optional[int] = 10,
        min_files: int = 2,
        max_retries: int = 3,
        skip_processed: bool = True,
        overwrite: bool = False
    ) -> ProcessingResult:
        """Process recommendations for all WAI folders in scholarship.
        
        Args:
            scholarship_folder: Path to scholarship folder (e.g., "data/Delaney_Wings").
            model: Primary LLM model to use (default: "ollama/llama3.2:3b").
            fallback_model: Fallback model if primary fails (default: "ollama/llama3:latest").
            max_wai_folders: Maximum number of WAI folders to process (default: 10).
            min_files: Minimum recommendation files required (default: 2).
            max_retries: Maximum retry attempts per WAI (default: 3).
            skip_processed: Skip already processed WAI folders (default: True).
            overwrite: Overwrite existing output files (default: False).
        
        Returns:
            ProcessingResult with statistics and errors.
        
        Example:
            >>> agent = RecommendationAgent()
            >>> result = agent.process_recommendations(
            ...     scholarship_folder="data/Delaney_Wings",
            ...     max_wai_folders=5,
            ...     min_files=2
            ... )
        """
        start_time = time.time()
        scholarship_path = Path(scholarship_folder)
        
        # Get scholarship name
        scholarship_name = get_scholarship_name_from_path(scholarship_path)
        
        logger.info("="*60)
        logger.info("Starting Recommendation Agent")
        logger.info("="*60)
        logger.info(f"Scholarship folder: {scholarship_folder}")
        logger.info(f"Scholarship name: {scholarship_name}")
        logger.info(f"Model: {model}")
        logger.info(f"Fallback model: {fallback_model}")
        logger.info(f"Max WAI folders: {max_wai_folders}")
        logger.info(f"Min files required: {min_files}")
        logger.info(f"Skip processed: {skip_processed}, Overwrite: {overwrite}")
        
        # Load criteria
        criteria = load_criteria(scholarship_path)
        criteria_path = get_criteria_path(scholarship_path)
        logger.info(f"Loaded criteria from: {criteria_path}")
        
        # Scan for WAI folders
        wai_folders = scan_scholarship_folder(str(scholarship_path))
        logger.info(f"Found {len(wai_folders)} WAI folders")
        
        # Limit number of folders if specified
        if max_wai_folders and len(wai_folders) > max_wai_folders:
            wai_folders = wai_folders[:max_wai_folders]
            logger.info(f"Limited to first {max_wai_folders} folders")
        
        # Process each WAI folder
        successful = 0
        failed = 0
        skipped = 0
        errors = []
        
        for i, wai_folder in enumerate(wai_folders, 1):
            wai_number = get_wai_number(wai_folder)
            logger.info(f"\n[{i}/{len(wai_folders)}] Processing WAI: {wai_number}")
            
            try:
                # Check if already processed
                output_path = get_recommendation_output_path(
                    Path("outputs"),
                    scholarship_name,
                    wai_number
                )
                
                if skip_processed and not overwrite and is_recommendation_processed(output_path):
                    logger.info(f"  Skipping {wai_number} (already processed)")
                    skipped += 1
                    continue
                
                # Process this WAI folder
                result = self._process_single_wai(
                    wai_folder=wai_folder,
                    wai_number=wai_number,
                    scholarship_name=scholarship_name,
                    criteria=criteria,
                    criteria_path=str(criteria_path),
                    model=model,
                    fallback_model=fallback_model,
                    min_files=min_files,
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
                error_msg = f"Unexpected error processing {wai_number}: {str(e)}"
                logger.error(f"  ✗ {error_msg}")
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
        min_files: int,
        max_retries: int
    ) -> Optional[RecommendationData]:
        """Process recommendations for a single WAI folder.
        
        Args:
            wai_folder: Path to WAI folder.
            wai_number: WAI application number.
            scholarship_name: Name of the scholarship.
            criteria: Evaluation criteria text.
            criteria_path: Path to criteria file.
            model: Primary LLM model.
            fallback_model: Fallback LLM model.
            min_files: Minimum files required.
            max_retries: Maximum retry attempts.
        
        Returns:
            RecommendationData if successful, None otherwise.
        """
        try:
            # Find recommendation files in unified output structure
            # Attachments are now in outputs/{scholarship}/{WAI}/attachments/
            output_base = Path("outputs")
            wai_attachments_dir = output_base / scholarship_name / wai_number / "attachments"
            
            # find_recommendation_files expects base dir, so we pass the parent
            # and it will look in {base}/{scholarship}/{WAI}/
            # But now we need to look in {base}/{scholarship}/{WAI}/attachments/
            # So we need to update the function call
            rec_files = find_recommendation_files(
                output_base,
                scholarship_name,
                wai_number,
                max_files=2
            )
            
            # Validate files
            is_valid, error_msg = validate_recommendation_files(rec_files, min_files)
            if not is_valid:
                logger.warning(f"  {error_msg}")
                return None
            
            logger.info(f"  Found {len(rec_files)} recommendation files")
            
            # Read recommendation texts
            rec_texts = []
            source_files = []
            for rec_file in rec_files:
                text = read_recommendation_text(rec_file)
                rec_texts.append(text)
                source_files.append(rec_file.name)
                logger.debug(f"  Read {len(text)} characters from {rec_file.name}")
            
            # Analyze with LLM (with retry logic)
            analysis_data = None
            current_model = model
            
            for attempt in range(max_retries):
                logger.info(f"  Analysis attempt {attempt + 1}/{max_retries} with {current_model}")
                
                try:
                    # Call LLM
                    llm_response = self._analyze_with_llm(
                        rec_texts,
                        criteria,
                        current_model
                    )
                    
                    # Extract JSON from response
                    json_data = extract_json_from_text(llm_response)
                    if not json_data:
                        logger.warning("  Could not extract JSON from LLM response")
                        if attempt < max_retries - 1:
                            current_model = fallback_model
                        continue
                    
                    # Validate and fix
                    is_valid, fixed_data, errors = validate_and_fix_iterative(
                        json_data,
                        self.schema,
                        max_attempts=3
                    )
                    
                    if is_valid:
                        analysis_data = fixed_data
                        logger.info(f"  ✓ Validation successful")
                        break
                    else:
                        logger.warning(f"  Validation failed: {len(errors)} errors")
                        if attempt < max_retries - 1:
                            current_model = fallback_model
                        
                except Exception as e:
                    logger.error(f"  Error in analysis attempt: {str(e)}")
                    if attempt < max_retries - 1:
                        current_model = fallback_model
            
            if not analysis_data:
                logger.error("  Failed to get valid analysis after all retries")
                return None
            
            # Create RecommendationData object
            rec_data = RecommendationData(
                wai_number=wai_number,
                summary=analysis_data.get("summary", ""),
                profile_features=analysis_data.get("profile_features", {}),
                scores=analysis_data.get("scores", {}),
                score_breakdown=analysis_data.get("score_breakdown", {}),
                source_files=source_files,
                model_used=current_model,
                criteria_used=criteria_path
            )
            
            # Save to JSON
            output_path = get_recommendation_output_path(
                Path("outputs"),
                scholarship_name,
                wai_number
            )
            self._save_json(rec_data, output_path)
            
            return rec_data
            
        except Exception as e:
            logger.error(f"  Error processing {wai_number}: {str(e)}")
            return None
    
    def _analyze_with_llm(
        self,
        recommendation_texts: list[str],
        criteria: str,
        model: str
    ) -> str:
        """Call LLM to analyze recommendations.
        
        Args:
            recommendation_texts: List of recommendation letter texts.
            criteria: Evaluation criteria.
            model: LLM model to use.
        
        Returns:
            LLM response as string.
        
        Raises:
            Exception: If LLM call fails.
        """
        # Build prompt (no longer passing schema - it's embedded in the prompt)
        prompt = build_analysis_prompt(recommendation_texts, criteria)
        
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
    
    def _save_json(self, data: RecommendationData, output_path: Path) -> bool:
        """Save recommendation data to JSON file.
        
        Args:
            data: RecommendationData object.
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
            
        except Exception as e:
            logger.error(f"  Error saving JSON: {str(e)}")
            return False


# Made with Bob
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

        from pathlib import Path
        from agents.academic_agent import AcademicAgent
        
        agent = AcademicAgent(Path("data/WAI-Harvard-June-2026"))
        result = agent.process_batch(
            wai_numbers=["WAI-12345", "WAI-12346"],
            model="ollama/llama3.2:3b"
        )
        
        print(f"Processed: {result.successful}/{result.total}")

Attributes:
    logger: Module-level logger instance for logging operations.
"""

import json
import logging
import time
from pathlib import Path
from typing import Optional

from litellm import completion

from utils.llm_config import configure_litellm
configure_litellm()

from models.academic_data import (
    AcademicData,
    ProcessingResult,
    ProcessingError
)
from utils.folder_scanner import scan_scholarship_folder, get_wai_number
from utils.resume_scanner import (
    read_resume_text,
    get_resume_output_path,
    is_resume_processed
)
from utils.prompt_loader import load_analysis_prompt, load_schema_path, load_repair_prompt, load_agent_config
from utils.attachment_finder import find_input_files_for_agent
from utils.schema_validator import (
    load_schema,
    extract_json_from_text
)
from utils.llm_repair import validate_and_repair_once, llm_repair_json
from .prompts import SYSTEM_PROMPT, build_analysis_prompt

logger = logging.getLogger(__name__)


class AcademicAgent:
    """Agent for analyzing academic/resume profiles using LLM.
    
    This agent processes resume/CV files from scholarship applications,
    analyzes them using LLM with scholarship-specific criteria, and generates
    structured JSON output with scores and detailed analysis.
    
    Attributes:
        scholarship_folder: Path to scholarship data folder.
        schema: JSON schema for output validation.
    
    Example:
        >>> agent = AcademicAgent(Path("data/WAI-Harvard-June-2026"))
        >>> result = agent.analyze_resume(wai_number="WAI-12345")
        >>> print(f"Overall score: {result.scores.overall_score}")
    """
    
    def __init__(self, scholarship_folder: Path):
        """Initialize the Academic Agent with scholarship configuration.
        
        Args:
            scholarship_folder: Path to scholarship data folder containing agents.json.
            
        Raises:
            FileNotFoundError: If the schema file cannot be found.
            ValueError: If the schema path is not configured in agents.json.
        """
        self.scholarship_folder = scholarship_folder
        self.scholarship_name = scholarship_folder.name
        
        # Load schema from agents.json config (resume artifact)
        schema_path = load_schema_path(scholarship_folder, "resume")
        if not schema_path:
            raise ValueError(
                f"No schema path configured for 'resume' agent in {scholarship_folder}/agents.json. "
                f"Run generate_artifacts.py to create the schema."
            )
        
        if not schema_path.exists():
            raise FileNotFoundError(
                f"Schema file not found: {schema_path}. "
                f"Run generate_artifacts.py to create the schema."
            )
        
        self.schema = load_schema(schema_path)
        logger.info(f"Loaded schema from: {schema_path}")
        logger.info(f"Academic Agent initialized for {self.scholarship_name}")
    
    def analyze_resume(
        self,
        wai_number: str,
        model: str = "ollama/llama3.2:3b",
        fallback_model: str = "ollama/llama3:latest",
        max_retries: int = 3
    ) -> Optional[AcademicData]:
        """Analyze resume/academic profile for a single WAI application.
        
        Args:
            wai_number: WAI application number.
            model: Primary LLM model to use.
            fallback_model: Fallback model if primary fails.
            max_retries: Maximum retry attempts.
        
        Returns:
            AcademicData if successful, None otherwise.
        """
        # Load analysis prompt from agents.json config (resume artifact)
        analysis_prompt = load_analysis_prompt(self.scholarship_folder, "resume")
        if not analysis_prompt:
            logger.error("No analysis prompt found for resume agent")
            return None
        
        # Process single WAI
        return self._process_single_wai(
            wai_number=wai_number,
            analysis_prompt=analysis_prompt,
            model=model,
            fallback_model=fallback_model,
            max_retries=max_retries
        )
    
    def process_batch(
        self,
        wai_numbers: list[str],
        model: str = "ollama/llama3.2:3b",
        fallback_model: str = "ollama/llama3:latest",
        max_retries: int = 3,
        skip_processed: bool = True,
        overwrite: bool = False
    ) -> ProcessingResult:
        """Process resumes for multiple WAI applications.
        
        Args:
            wai_numbers: List of WAI numbers to process.
            model: Primary LLM model to use.
            fallback_model: Fallback model if primary fails.
            max_retries: Maximum retry attempts per WAI.
            skip_processed: Skip already processed WAI folders.
            overwrite: Overwrite existing output files.
        
        Returns:
            ProcessingResult with statistics and errors.
        """
        start_time = time.time()
        
        logger.info("="*60)
        logger.info("Starting Academic/Resume Agent Batch")
        logger.info("="*60)
        logger.info(f"Scholarship: {self.scholarship_name}")
        logger.info(f"Model: {model}")
        logger.info(f"WAI count: {len(wai_numbers)}")
        
        # Load analysis prompt from agents.json config (resume artifact)
        analysis_prompt = load_analysis_prompt(self.scholarship_folder, "resume")
        if not analysis_prompt:
            logger.error("No analysis prompt found for resume agent")
            return ProcessingResult(
                total=len(wai_numbers),
                successful=0,
                failed=len(wai_numbers),
                skipped=0,
                errors=[],
                duration=0
            )
        
        # Process each WAI
        successful = 0
        failed = 0
        skipped = 0
        errors = []
        
        for idx, wai_number in enumerate(wai_numbers, 1):
            logger.info(f"\n[{idx}/{len(wai_numbers)}] Processing WAI: {wai_number}")
            
            try:
                # Check if already processed
                output_path = get_resume_output_path(
                    Path("outputs"),
                    self.scholarship_name,
                    wai_number
                )
                
                if skip_processed and not overwrite and is_resume_processed(output_path):
                    logger.info(f"  ✓ Already processed, skipping")
                    skipped += 1
                    continue
                
                # Process this WAI
                result = self._process_single_wai(
                    wai_number=wai_number,
                    analysis_prompt=analysis_prompt,
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
        
        result = ProcessingResult(
            total=len(wai_numbers),
            successful=successful,
            failed=failed,
            skipped=skipped,
            errors=errors,
            duration=duration
        )
        
        # Log summary
        logger.info("\n" + "="*60)
        logger.info("Processing complete!")
        logger.info(f"Total: {result.total}, Successful: {successful}, Failed: {failed}, Skipped: {skipped}")
        logger.info(f"Duration: {duration:.2f}s, Average: {result.average_per_wai:.2f}s per WAI")
        logger.info("="*60)
        
        return result
    
    def _process_single_wai(
        self,
        wai_number: str,
        analysis_prompt: str,
        model: str,
        fallback_model: str,
        max_retries: int
    ) -> Optional[AcademicData]:
        """Process resume for a single WAI application.
        
        Args:
            wai_number: WAI application number.
            analysis_prompt: Analysis prompt text from agents.json config.
            model: Primary LLM model.
            fallback_model: Fallback LLM model.
            max_retries: Maximum retry attempts.
        
        Returns:
            AcademicData if successful, None otherwise.
        """
        try:
            output_base = Path("outputs")
            
            # Find resume files using agents.json config
            resume_files = find_input_files_for_agent(
                self.scholarship_folder, "resume", wai_number, output_base
            )
            
            if not resume_files:
                logger.warning(f"  No resume file found for {wai_number}")
                return None
            
            # Use first file (resume is typically a single file)
            resume_file = resume_files[0]
            logger.info(f"  Found resume file: {resume_file.name}")
            
            # Read resume text
            resume_text = read_resume_text(resume_file)
            
            # Try analysis with retries
            for attempt in range(1, max_retries + 1):
                try:
                    current_model = model if attempt == 1 else fallback_model
                    logger.info(f"  Analysis attempt {attempt}/{max_retries} with {current_model}")
                    
                    # Analyze with LLM
                    response_text = self._analyze_with_llm(resume_text, analysis_prompt, current_model)
                    
                    # Extract and validate JSON (local auto-fix pass)
                    extracted = extract_json_from_text(response_text)
                    if extracted is None:
                        errors = ["root: Could not extract valid JSON from LLM response"]
                        repair_template = load_repair_prompt(self.scholarship_folder, "resume")
                        if repair_template:
                            repaired = llm_repair_json(
                                repair_template=repair_template,
                                invalid_json={"raw_response": response_text},
                                validation_errors=errors,
                                model=current_model,
                                system_prompt=SYSTEM_PROMPT,
                                max_tokens=3000,
                            )
                            if repaired is not None:
                                is_valid, fixed_data, errors = validate_and_repair_once(
                                    data=repaired,
                                    schema=self.schema,
                                    repair_template=None,  # already a repair attempt
                                    model=current_model,
                                    system_prompt=SYSTEM_PROMPT,
                                    local_fix_attempts=3,
                                    repair_max_tokens=3000,
                                )
                            else:
                                is_valid = False
                                fixed_data = {}
                        else:
                            is_valid = False
                            fixed_data = {}
                    else:
                        repair_template = load_repair_prompt(self.scholarship_folder, "resume")
                        is_valid, fixed_data, errors = validate_and_repair_once(
                            data=extracted,
                            schema=self.schema,
                            repair_template=repair_template,
                            model=current_model,
                            system_prompt=SYSTEM_PROMPT,
                            local_fix_attempts=3,
                            repair_max_tokens=3000,
                        )
                    
                    if is_valid and fixed_data:
                        #logger.info(f"  ✓ Validation successful")
                        break
                    else:
                        logger.warning(f"  Validation failed: {errors}")

                        if attempt == max_retries:
                            logger.error("  Max retries reached; unable to produce valid schema output")
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
                criteria_used=(load_agent_config(self.scholarship_folder, "resume") or {}).get(
                    "analysis_prompt", "prompts/resume_analysis.txt"
                ),
            )
            
            # Save to JSON
            output_path = get_resume_output_path(
                Path("outputs"),
                self.scholarship_name,
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
        analysis_prompt: str,
        model: str
    ) -> str:
        """Call LLM to analyze resume.
        
        Args:
            resume_text: Content of the resume/CV.
            analysis_prompt: Analysis prompt from agents.json config.
            model: LLM model to use.
        
        Returns:
            LLM response as string.
        
        Raises:
            Exception: If LLM call fails.
        """
        # Build prompt using the analysis prompt from config
        prompt = build_analysis_prompt(resume_text, analysis_prompt)
        
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
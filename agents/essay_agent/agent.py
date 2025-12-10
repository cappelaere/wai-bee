"""Essay Agent for analyzing personal essays.

This module provides the EssayAgent class for analyzing personal essays
and extracting motivation, goals, character traits, and leadership qualities.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-06
Version: 1.0.0
License: MIT
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

from models.essay_data import EssayData
from utils.essay_scanner import find_essay_files, read_essay_text, has_essay_files
from utils.criteria_loader import load_criteria
from utils.schema_validator import (
    load_schema,
    validate_and_fix_iterative,
    extract_json_from_text
)
from agents.essay_agent.prompts import build_essay_analysis_prompt


class EssayAgent:
    """Agent for analyzing personal essays and extracting profile information.
    
    This agent processes personal essays (files 4 and 5) to evaluate:
    - Aviation passion and motivation
    - Career goals and clarity
    - Personal character traits
    - Leadership and community service
    - Alignment with WAI values
    
    Attributes:
        schema: JSON schema for output validation.
        schema_path: Path to the schema file.
    """
    
    def __init__(self, schema_path: Optional[Path] = None):
        """Initialize Essay Agent.
        
        Args:
            schema_path: Path to JSON schema file. If None, uses default path.
        """
        self.logger = logging.getLogger()
        self.schema_path = schema_path or Path("schemas/essay_agent_schema.json")
        self.schema = load_schema(self.schema_path)
        self.logger.info("Essay Agent initialized")
    
    def analyze_essays(
        self,
        attachments_dir: Path,
        scholarship_name: str,
        wai_number: str,
        criteria_path: Path,
        model: str = "ollama/llama3.2:3b",
        fallback_model: str = "ollama/llama3:latest",
        max_retries: int = 3,
        output_dir: Optional[Path] = None
    ) -> Optional[EssayData]:
        """Analyze personal essays for a WAI application.
        
        Args:
            attachments_dir: Base attachments directory.
            scholarship_name: Name of scholarship.
            wai_number: WAI application number.
            criteria_path: Path to evaluation criteria file.
            model: Primary LLM model to use.
            fallback_model: Fallback LLM model.
            max_retries: Maximum retry attempts.
            output_dir: Optional output directory for JSON results.
            
        Returns:
            EssayData object with analysis results, or None if processing fails.
        """
        start_time = time.time()
        self.logger.info(f"Starting essay analysis for WAI {wai_number}")
        
        try:
            # Find essay files (files 4 and 5) in unified output structure
            # Attachments are now in outputs/{scholarship}/{WAI}/attachments/
            output_base = Path("outputs")
            essay_files = find_essay_files(output_base, scholarship_name, wai_number)
            
            if not essay_files:
                self.logger.warning(f"No essay files found for WAI {wai_number}")
                return None
            
            # Read essay texts
            essay_texts = []
            source_files = []
            for essay_file in essay_files:
                text = read_essay_text(essay_file)
                essay_texts.append(text)
                source_files.append(essay_file.name)
            
            self.logger.info(f"Processing {len(essay_texts)} essay file(s)")
            
            # Load evaluation criteria
            # If criteria_path is a file, read it directly; if folder, use load_criteria
            if criteria_path.is_file():
                criteria = criteria_path.read_text(encoding='utf-8')
                self.logger.info(f"Loaded criteria from: {criteria_path}")
            else:
                criteria = load_criteria(criteria_path, criteria_type="essay")
            
            # Analyze essays with LLM (with retry logic)
            analysis_data = None
            current_model = model
            
            for attempt in range(max_retries):
                self.logger.info(f"  Analysis attempt {attempt + 1}/{max_retries} with {current_model}")
                
                try:
                    # Call LLM
                    llm_response = self._analyze_with_llm(
                        essay_texts,
                        criteria,
                        current_model
                    )
                    
                    # Extract JSON from response
                    json_data = extract_json_from_text(llm_response)
                    if not json_data:
                        self.logger.warning("  Could not extract JSON from LLM response")
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
                        self.logger.info(f"  ✓ Validation successful")
                        break
                    else:
                        self.logger.warning(f"  Validation failed: {len(errors)} errors")
                        if attempt < max_retries - 1:
                            current_model = fallback_model
                        
                except Exception as e:
                    self.logger.error(f"  Error in analysis attempt: {str(e)}")
                    if attempt < max_retries - 1:
                        current_model = fallback_model
            
            if not analysis_data:
                self.logger.error("  Failed to get valid analysis after all retries")
                return None
            
            # Create EssayData object
            essay_data = EssayData(
                wai_number=wai_number,
                summary=analysis_data.get("summary", "Unknown"),
                profile_features=analysis_data.get("profile_features", {}),
                scores=analysis_data.get("scores", {}),
                score_breakdown=analysis_data.get("score_breakdown", {}),
                source_files=source_files,
                model_used=current_model,
                criteria_used=str(criteria_path)
            )
            
            # Save to output directory if provided
            if output_dir:
                self._save_results(essay_data, output_dir, scholarship_name, wai_number)
            
            duration = time.time() - start_time
            self.logger.info(f"Essay analysis completed for WAI {wai_number} in {duration:.2f}s")
            self.logger.info(f"Overall score: {essay_data.scores.overall_score}")
            
            return essay_data
            
        except Exception as e:
            duration = time.time() - start_time
            self.logger.error(f"Error analyzing essays for WAI {wai_number}: {e}", exc_info=True)
            self.logger.info(f"Failed after {duration:.2f}s")
            return None
    
    def _analyze_with_llm(
        self,
        essay_texts: list[str],
        criteria: str,
        model: str
    ) -> str:
        """Call LLM to analyze essays.
        
        Args:
            essay_texts: List of essay text content.
            criteria: Evaluation criteria text.
            model: LLM model to use.
            
        Returns:
            LLM response as string.
            
        Raises:
            Exception: If LLM call fails.
        """
        # Build prompt
        prompt = build_essay_analysis_prompt(essay_texts, criteria)
        
        # Call LLM
        response = completion(
            model=model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=2000
        )
        
        # Extract content from response
        content = response.choices[0].message.content
        return content if content else ""
    
    def _save_results(
        self,
        essay_data: EssayData,
        output_dir: Path,
        scholarship_name: str,
        wai_number: str
    ) -> None:
        """Save essay analysis results to JSON file.
        
        Args:
            essay_data: Essay analysis data to save.
            output_dir: Output directory path.
            scholarship_name: Name of scholarship.
            wai_number: WAI application number.
        """
        # Create output directory structure
        wai_output_dir = output_dir / scholarship_name / wai_number
        wai_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save JSON file
        output_file = wai_output_dir / "essay_analysis.json"
        
        # Convert to dict and save
        data_dict = essay_data.model_dump(mode='json')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data_dict, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Saved essay analysis to {output_file}")
    
    def process_batch(
        self,
        attachments_dir: Path,
        scholarship_name: str,
        criteria_path: Path,
        output_dir: Path,
        model: str = "ollama/llama3.2:3b",
        fallback_model: str = "ollama/llama3:latest",
        max_retries: int = 3,
        wai_numbers: Optional[list[str]] = None
    ) -> dict:
        """Process multiple WAI applications in batch.
        
        Args:
            attachments_dir: Base attachments directory (kept for compatibility, but now uses outputs base).
            scholarship_name: Name of scholarship.
            criteria_path: Path to evaluation criteria file.
            output_dir: Output directory for results.
            model: Primary LLM model to use.
            fallback_model: Fallback LLM model.
            max_retries: Maximum retry attempts.
            wai_numbers: Optional list of specific WAI numbers to process.
                        If None, processes all WAI folders found.
            
        Returns:
            Dictionary with processing statistics.
        """
        start_time = time.time()
        
        # Use unified output structure
        output_base = Path("outputs")
        
        # Get list of WAI numbers to process
        scholarship_dir = output_base / scholarship_name
        
        if wai_numbers is None:
            # Process all WAI folders
            wai_dirs = [d for d in scholarship_dir.iterdir() if d.is_dir()]
            wai_numbers = [d.name for d in wai_dirs]
        
        total = len(wai_numbers)
        successful = 0
        failed = 0
        skipped = 0
        
        self.logger.info(f"Starting batch processing of {total} WAI applications")
        
        for i, wai_number in enumerate(wai_numbers, 1):
            self.logger.info(f"Processing {i}/{total}: WAI {wai_number}")
            
            # Check if essays exist in unified structure
            if not has_essay_files(output_base, scholarship_name, wai_number):
                self.logger.info(f"  Skipping {wai_number} (no essay files)")
                skipped += 1
                continue
            
            try:
                result = self.analyze_essays(
                    attachments_dir,
                    scholarship_name,
                    wai_number,
                    criteria_path,
                    model,
                    fallback_model,
                    max_retries,
                    output_dir
                )
                
                if result:
                    successful += 1
                    self.logger.info(f"  ✓ Successfully processed {wai_number}")
                else:
                    skipped += 1
                    
            except Exception as e:
                self.logger.error(f"Failed to process WAI {wai_number}: {e}")
                failed += 1
        
        duration = time.time() - start_time
        
        stats = {
            "total": total,
            "successful": successful,
            "failed": failed,
            "skipped": skipped,
            "duration": duration,
            "average_per_wai": duration / successful if successful > 0 else 0
        }
        
        self.logger.info(f"Batch processing completed in {duration:.2f}s")
        self.logger.info(f"Results: {successful} successful, {failed} failed, {skipped} skipped")
        
        return stats

# Made with Bob

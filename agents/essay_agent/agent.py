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
import time
from pathlib import Path
from typing import Optional

from litellm import completion

from utils.llm_config import configure_litellm
configure_litellm()

from models.essay_data import EssayData
from utils.essay_scanner import read_essay_text
from utils.attachment_finder import find_input_files_for_agent
from utils.prompt_loader import load_analysis_prompt, load_repair_prompt, load_schema_path, load_agent_config
from utils.schema_validator import (
    load_schema,
    extract_json_from_text
)
from utils.llm_repair import validate_and_repair_once
from agents.essay_agent.prompts import build_essay_analysis_prompt


class EssayAgent:
    """Agent for analyzing personal essays and extracting profile information.
    
    This agent processes personal essays to evaluate leadership qualities,
    career goals, and program alignment based on configurable facets.
    
    Attributes:
        scholarship_folder: Path to scholarship data folder.
        schema: JSON schema for output validation.
    """
    
    def __init__(self, scholarship_folder: Path):
        """Initialize Essay Agent with scholarship configuration.
        
        Args:
            scholarship_folder: Path to scholarship data folder containing agents.json.
            
        Raises:
            FileNotFoundError: If the schema file cannot be found.
            ValueError: If the schema path is not configured in agents.json.
        """
        self.logger = logging.getLogger(__name__)
        self.scholarship_folder = scholarship_folder
        self.scholarship_name = scholarship_folder.name
        
        # Load schema from agents.json config
        schema_path = load_schema_path(scholarship_folder, "essay")
        if not schema_path:
            raise ValueError(
                f"No schema path configured for 'essay' agent in {scholarship_folder}/agents.json. "
                f"Run generate_artifacts.py to create the schema."
            )
        
        if not schema_path.exists():
            raise FileNotFoundError(
                f"Schema file not found: {schema_path}. "
                f"Run generate_artifacts.py to create the schema."
            )
        
        self.schema = load_schema(schema_path)
        self.logger.info(f"Loaded schema from: {schema_path}")
        self.logger.info(f"Essay Agent initialized for {self.scholarship_name}")
    
    def analyze_essays(
        self,
        wai_number: str,
        model: str = "ollama/llama3.2:3b",
        fallback_model: str = "ollama/llama3:latest",
        max_retries: int = 3,
        output_dir: Optional[Path] = None
    ) -> Optional[EssayData]:
        """Analyze personal essays for a WAI application.
        
        Args:
            wai_number: WAI application number.
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
            output_base = Path("outputs")
            
            # Find essay files using agents.json config
            essay_files = find_input_files_for_agent(
                self.scholarship_folder, "essay", wai_number, output_base
            )
            
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
            
            # Load analysis prompt from agents.json config
            analysis_prompt = load_analysis_prompt(self.scholarship_folder, "essay")
            if not analysis_prompt:
                self.logger.error("No analysis prompt found for essay agent")
                return None
            self.logger.info(f"Loaded analysis prompt from agents.json config")
            
            # Analyze essays with LLM (with retry logic)
            analysis_data = None
            current_model = model
            
            for attempt in range(max_retries):
                self.logger.info(f"  Analysis attempt {attempt + 1}/{max_retries} with {current_model}")
                
                try:
                    # Call LLM
                    llm_response = self._analyze_with_llm(
                        essay_texts,
                        analysis_prompt,
                        current_model
                    )
                    
                    # Extract JSON from response
                    json_data = extract_json_from_text(llm_response)
                    if not json_data:
                        self.logger.warning("  Could not extract JSON from LLM response")
                        if attempt < max_retries - 1:
                            current_model = fallback_model
                        continue
                    
                    # Validate, auto-fix, then optionally repair once via LLM
                    repair_template = load_repair_prompt(self.scholarship_folder, "essay")
                    is_valid, fixed_data, errors = validate_and_repair_once(
                        data=json_data,
                        schema=self.schema,
                        repair_template=repair_template,
                        model=current_model,
                        system_prompt=None,
                        local_fix_attempts=3,
                        repair_max_tokens=2000,
                    )
                    
                    if is_valid:
                        analysis_data = fixed_data
                        #self.logger.info(f"  ✓ Validation successful")
                        break
                    else:
                        self.logger.warning(f"  Validation failed: {len(errors)} errors")

                        if attempt < max_retries - 1:
                            current_model = fallback_model
                        
                except Exception:
                    self.logger.exception(f"  Error in analysis attempt {attempt} for {wai_number}")
                    if attempt < max_retries - 1:
                        current_model = fallback_model
            
            if not analysis_data:
                self.logger.error("  Failed to get valid analysis after all retries")
                return None
            
            # Create EssayData object
            scores=analysis_data.get("scores", {})
           
            # Calculate from component scores
            overall = (
                scores.get('motivation_score', 0) +
                scores.get('goals_clarity_score', 0) +
                scores.get('character_service_leadership_score', 0)
            )
            scores['overall_score'] = int(overall)
            self.logger.debug(f"Calculated essay overall_score: {scores['overall_score']}")
            
            essay_data = EssayData(
                wai_number=wai_number,
                summary=analysis_data.get("summary", "Unknown"),
                profile_features=analysis_data.get("profile_features", {}),
                score_breakdown=analysis_data.get("score_breakdown", {}),
                source_files=source_files,
                model_used=current_model,
                criteria_used=(load_agent_config(self.scholarship_folder, "essay") or {}).get(
                    "analysis_prompt", "prompts/essay_analysis.txt"
                ),
                scores=scores
            )
            
            # Save to output directory if provided
            if output_dir:
                self._save_results(essay_data, output_dir, self.scholarship_name, wai_number)
            
            duration = time.time() - start_time
            self.logger.info(f"Essay analysis completed for WAI {wai_number} in {duration:.2f}s")
            self.logger.info(f"Overall score: {essay_data.scores.overall_score}")
            
            return essay_data
            
        except Exception:
            duration = time.time() - start_time
            self.logger.exception(f"Error analyzing essays for WAI {wai_number}")
            self.logger.info(f"Failed after {duration:.2f}s")
            return None
    
    def _analyze_with_llm(
        self,
        essay_texts: list[str],
        analysis_prompt: str,
        model: str
    ) -> str:
        """Call LLM to analyze essays.
        
        Args:
            essay_texts: List of essay text content.
            analysis_prompt: Analysis prompt from agents.json config.
            model: LLM model to use.
            
        Returns:
            LLM response as string.
            
        Raises:
            Exception: If LLM call fails.
        """
        # Build prompt
        prompt = build_essay_analysis_prompt(essay_texts, analysis_prompt)
        
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
        wai_numbers: list[str],
        model: str = "ollama/llama3.2:3b",
        fallback_model: str = "ollama/llama3:latest",
        max_retries: int = 3,
        output_dir: Optional[Path] = None
    ) -> dict:
        """Process multiple WAI applications in batch.
        
        Args:
            wai_numbers: List of WAI numbers to process.
            model: Primary LLM model to use.
            fallback_model: Fallback LLM model.
            max_retries: Maximum retry attempts.
            output_dir: Output directory for results.
            
        Returns:
            Dictionary with processing statistics.
        """
        start_time = time.time()
        
        total = len(wai_numbers)
        successful = 0
        failed = 0
        skipped = 0
        
        self.logger.info(f"Starting batch processing of {total} WAI applications")
        
        for i, wai_number in enumerate(wai_numbers, 1):
            self.logger.info(f"Processing {i}/{total}: WAI {wai_number}")
            
            try:
                result = self.analyze_essays(
                    wai_number=wai_number,
                    model=model,
                    fallback_model=fallback_model,
                    max_retries=max_retries,
                    output_dir=output_dir
                )
                
                if result:
                    successful += 1
                    self.logger.info(f"  ✓ Successfully processed {wai_number}")
                else:
                    skipped += 1
                    
            except Exception:
                self.logger.exception(f"Failed to process WAI {wai_number}")
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

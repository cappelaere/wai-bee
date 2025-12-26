"""LLM service for application processing.

This module handles all LLM interactions for extracting and scoring applications.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-07
Version: 1.0.0
License: MIT
"""

import json
import logging
import re
from typing import Optional
from pathlib import Path

from litellm import completion

from models.application_data import ApplicationData
from models.application_score import ApplicationAnalysis
from .prompts import (
    SYSTEM_PROMPT,
    get_extraction_prompt,
    SCORING_SYSTEM_PROMPT,
    get_scoring_prompt
)

logger = logging.getLogger(__name__)


class LLMService:
    """Service for LLM-based extraction and scoring operations."""
    
    @staticmethod
    def extract_json_from_response(response_text: str) -> Optional[dict]:
        """Extract JSON object from LLM response text.
        
        Attempts to parse the response as JSON. If that fails, removes markdown
        code fences and tries again, then uses regex to find JSON objects.
        
        Args:
            response_text: Response text from the LLM.
        
        Returns:
            Parsed JSON dictionary if found, None otherwise.
        """
        # Try to parse the entire response as JSON
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass
        
        # Remove markdown code fences if present
        cleaned_text = response_text.strip()
        if cleaned_text.startswith('```'):
            # Remove opening fence (```json or ```)
            cleaned_text = re.sub(r'^```(?:json)?\s*\n?', '', cleaned_text)
            # Remove closing fence
            cleaned_text = re.sub(r'\n?```\s*$', '', cleaned_text)
            
            try:
                return json.loads(cleaned_text)
            except json.JSONDecodeError:
                pass
        
        # Try to find JSON object in the response using regex
        json_match = re.search(r'\{.*\}', cleaned_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
        
        logger.error(f"Could not extract JSON from response: {response_text[:200]}")
        return None
    
    @staticmethod
    def has_unknown_fields(data: ApplicationData) -> bool:
        """Check if ApplicationData has any Unknown field values.
        
        Args:
            data: The application data to check.
        
        Returns:
            True if any field (name, city, state, country) is "Unknown".
        """
        return (
            data.name == "Unknown" or
            data.city == "Unknown" or
            data.country == "Unknown" or
            (data.state == "Unknown" if data.state is not None else False)
        )
    
    @staticmethod
    def extract_information(
        document_text: str,
        wai_number: str,
        source_file: str,
        model: str
    ) -> Optional[ApplicationData]:
        """Extract applicant information from document text using LLM.
        
        Args:
            document_text: Parsed text content from the application document.
            wai_number: WAI number of the applicant.
            source_file: Name of the source application file.
            model: LLM model to use for extraction.
        
        Returns:
            Extracted application data if successful, None if extraction fails.
        """
        try:
            # Generate prompt
            user_prompt = get_extraction_prompt(document_text)
            
            # Call LLM using litellm
            response = completion(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1
            )
            
            # Extract response text
            response_text = response.choices[0].message.content or ""
            
            # Try to extract JSON from response
            json_data = LLMService.extract_json_from_response(str(response_text))
            
            if not json_data:
                logger.error("Failed to extract JSON from LLM response")
                return None
            
            # Create ApplicationData object
            state_value = json_data.get('state')
            # Convert null/None to None, keep valid state values
            if state_value in [None, 'null', 'None', '']:
                state_value = None
            elif state_value == 'Unknown':
                state_value = 'Unknown'
            
            app_data = ApplicationData(
                wai_number=wai_number,
                name=json_data.get('name', 'Unknown'),
                city=json_data.get('city', 'Unknown'),
                state=state_value,
                country=json_data.get('country', 'Unknown'),
                source_file=source_file
            )
            
            # Build location string for logging
            location_parts = [app_data.city]
            if app_data.state:
                location_parts.append(app_data.state)
            location_parts.append(app_data.country)
            location_str = ", ".join(location_parts)
            
            logger.info(f"Extracted: {app_data.name} from {location_str}")
            return app_data
            
        except Exception:
            logger.exception(f"Error extracting information for WAI {wai_number} from {source_file}")
            return None
    
    @staticmethod
    def extract_information_with_retry(
        document_text: str,
        wai_number: str,
        source_file: str,
        model: str,
        fallback_model: Optional[str],
        max_retries: int
    ) -> Optional[ApplicationData]:
        """Extract applicant information with retry logic and fallback model.
        
        Args:
            document_text: Parsed text content from the application document.
            wai_number: WAI number of the applicant.
            source_file: Name of the source application file.
            model: Primary LLM model to use for extraction.
            fallback_model: Fallback model if primary fails or returns Unknown.
            max_retries: Maximum retry attempts per model.
        
        Returns:
            Extracted application data if successful, None if all attempts fail.
        """
        best_result = None
        
        # Try with primary model
        for attempt in range(1, max_retries + 1):
            if attempt > 1:
                logger.info(f"Retry attempt {attempt}/{max_retries} with model: {model}")
            
            result = LLMService.extract_information(document_text, wai_number, source_file, model)
            if result:
                # Check if result has any Unknown values
                if LLMService.has_unknown_fields(result):
                    state_info = f", state={result.state}" if result.state else ""
                    logger.info(f"Primary model returned Unknown values: name={result.name}, city={result.city}{state_info}, country={result.country}")
                    best_result = result  # Keep as fallback
                    continue
                else:
                    # All fields extracted successfully
                    return result
        
        # If primary model failed or returned Unknown values, try fallback
        if fallback_model:
            if best_result:
                logger.warning(f"Primary model returned Unknown values, trying fallback: {fallback_model}")
            else:
                logger.warning(f"Primary model failed after {max_retries} attempts, trying fallback: {fallback_model}")
            
            for attempt in range(1, max_retries + 1):
                if attempt > 1:
                    logger.info(f"Fallback retry attempt {attempt}/{max_retries}")
                
                result = LLMService.extract_information(document_text, wai_number, source_file, fallback_model)
                if result:
                    # Check if fallback result is better than primary
                    if not LLMService.has_unknown_fields(result):
                        logger.info(f"Successfully extracted complete data using fallback model: {fallback_model}")
                        return result
                    elif best_result is None:
                        best_result = result
        
        # Return best result we got, even if it has Unknown values
        if best_result:
            logger.warning(f"Returning result with Unknown values as best available")
            return best_result
        
        logger.error(f"Failed to extract information after all attempts")
        return None
    
    @staticmethod
    def score_application(
        app_data: ApplicationData,
        scholarship_folder: Path,
        wai_number: str,
        output_dir: Path,
        model: str,
        max_retries: int
    ) -> Optional[ApplicationAnalysis]:
        """Score an application for completeness and validity.
        
        Args:
            app_data: Extracted application data.
            scholarship_folder: Path to scholarship folder.
            wai_number: WAI application number.
            output_dir: Base output directory.
            model: LLM model to use for scoring.
            max_retries: Maximum retry attempts.
        
        Returns:
            ApplicationAnalysis if successful, None otherwise.
        """
        try:
            # Load criteria
            criteria_path = scholarship_folder / "criteria" / "application_criteria.txt"
            if not criteria_path.exists():
                logger.warning(f"Application criteria not found: {criteria_path}")
                return None
            
            with open(criteria_path, 'r', encoding='utf-8') as f:
                criteria = f.read()
            
            # Get list of attachment files from the application data
            # The attachment_files_checked field contains the actual file information
            attachment_files = []
            if hasattr(app_data, 'attachment_files_checked') and app_data.attachment_files_checked:
                # Extract valid attachment file names
                attachment_files = [
                    f['name'] for f in app_data.attachment_files_checked
                    if f.get('valid', False)
                ]
            
            # Generate scoring prompt
            user_prompt = get_scoring_prompt(
                name=app_data.name,
                city=app_data.city,
                state=app_data.state or "N/A",
                country=app_data.country,
                attachment_files=attachment_files,
                criteria=criteria
            )
            
            # Call LLM with retry logic
            for attempt in range(1, max_retries + 1):
                try:
                    if attempt > 1:
                        logger.info(f"Scoring retry attempt {attempt}/{max_retries}")
                    
                    response = completion(
                        model=model,
                        messages=[
                            {"role": "system", "content": SCORING_SYSTEM_PROMPT},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.1
                    )
                    
                    response_text = response.choices[0].message.content or ""
                    
                    # Extract JSON from response
                    score_data = LLMService.extract_json_from_response(response_text)
                    if not score_data:
                        logger.warning(f"Failed to extract JSON from scoring response (attempt {attempt})")
                        continue
                    
                    # Calculate overall_score if missing
                    scores = score_data.get('scores', {})
                    
                    # Calculate from component scores
                    overall = (
                        scores.get('completeness_score', 0) +
                        scores.get('validity_score', 0) +
                        scores.get('attachment_score', 0)
                    )
                    scores['overall_score'] = int(overall)
                    logger.debug(f"Calculated application overall_score: {scores['overall_score'] }")
                    
                    # Create ApplicationAnalysis object
                    analysis = ApplicationAnalysis(
                        wai_number=wai_number,
                        summary=score_data.get('summary', ''),
                        scores=scores,
                        score_breakdown=score_data.get('score_breakdown', {}),
                        completeness_issues=score_data.get('completeness_issues', []),
                        validity_issues=score_data.get('validity_issues', []),
                        attachment_status=score_data.get('attachment_status', ''),
                        source_file=app_data.source_file,
                        model_used=model,
                        criteria_used=str(criteria_path)
                    )
                    
                    logger.info(f"Application scored: {analysis.scores.overall_score}/100")
                    return analysis
                    
                except Exception:
                    logger.exception(f"Scoring attempt {attempt} failed for WAI {wai_number}")
                    if attempt == max_retries:
                        logger.error(f"All scoring attempts failed for WAI {wai_number}")
                        return None
            
            return None
            
        except Exception:
            logger.exception(f"Error scoring application for WAI {wai_number}")
            return None


# Made with Bob
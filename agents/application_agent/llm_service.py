"""LLM service for application processing.

This module handles all LLM interactions for extracting and scoring applications.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-07
Version: 1.0.0
License: MIT
"""

import json
import logging
from typing import Optional
from pathlib import Path

from litellm import completion

from models.application_data import ApplicationData
from utils.prompt_loader import load_analysis_prompt, load_repair_prompt, load_schema_path
from utils.schema_validator import load_schema, extract_json_from_text
from utils.llm_repair import validate_and_repair_once
from .prompts import SYSTEM_PROMPT, get_extraction_prompt

logger = logging.getLogger(__name__)


class LLMService:
    """Service for LLM-based extraction and scoring operations."""
    
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
            json_data = extract_json_from_text(str(response_text))
            
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
    ) -> Optional[dict]:
        """Score an application using the generated facet-based prompt/schema.
        
        Args:
            app_data: Extracted application data.
            scholarship_folder: Path to scholarship folder (contains agents.json).
            wai_number: WAI application number.
            output_dir: Base output directory.
            model: LLM model to use for scoring.
            max_retries: Maximum retry attempts.
        
        Returns:
            Dict matching schemas_generated/application_analysis.schema.json, or None.
        """
        try:
            analysis_prompt = load_analysis_prompt(scholarship_folder, "application")
            if not analysis_prompt:
                logger.error("No analysis prompt found for application agent")
                return None

            schema_path = load_schema_path(scholarship_folder, "application")
            if not schema_path or not schema_path.exists():
                logger.error(f"Application schema not found: {schema_path}")
                return None
            schema = load_schema(schema_path)
            
            # Get list of attachment files from the application data
            # The attachment_files_checked field contains the actual file information
            attachment_files = []
            if hasattr(app_data, 'attachment_files_checked') and app_data.attachment_files_checked:
                # Extract valid attachment file names
                attachment_files = [
                    f['name'] for f in app_data.attachment_files_checked
                    if f.get('valid', False)
                ]
            
            state_display = app_data.state if app_data.state else "N/A (non-US applicant)"
            attachment_list = "\n".join(f"- {f}" for f in attachment_files) if attachment_files else "- None"
            artifact_context = (
                "APPLICATION DATA (extracted):\n"
                f"- name: {app_data.name}\n"
                f"- city: {app_data.city}\n"
                f"- state: {state_display}\n"
                f"- country: {app_data.country}\n"
                "\n"
                "ATTACHMENT FILES FOUND:\n"
                f"{attachment_list}\n"
            )

            user_prompt = f"{analysis_prompt}\n\n---\n\n## Application Content\n\n{artifact_context}"
            
            # Call LLM with retry logic
            for attempt in range(1, max_retries + 1):
                try:
                    if attempt > 1:
                        logger.info(f"Scoring retry attempt {attempt}/{max_retries}")
                    
                    response = completion(
                        model=model,
                        messages=[
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=0.1
                    )
                    
                    response_text = response.choices[0].message.content or ""
                    
                    extracted = extract_json_from_text(response_text)
                    if extracted is None:
                        logger.warning(f"Failed to extract JSON from scoring response (attempt {attempt})")
                        continue

                    repair_template = load_repair_prompt(scholarship_folder, "application")
                    is_valid, fixed_data, errors = validate_and_repair_once(
                        data=extracted,
                        schema=schema,
                        repair_template=repair_template,
                        model=model,
                        system_prompt=None,
                        local_fix_attempts=3,
                        repair_max_tokens=3000,
                    )
                    if is_valid:
                        return fixed_data

                    logger.warning(f"Schema validation failed: {len(errors)} errors")
                    
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
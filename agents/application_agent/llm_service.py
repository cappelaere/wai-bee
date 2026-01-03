"""LLM service for application processing.

This module handles all LLM interactions for extracting applicant information.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-07
Version: 1.0.0
License: MIT
"""

import json
import logging
from typing import Optional

from litellm import completion

from models.application_data import ApplicationData
from utils.schema_validator import extract_json_from_text
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

            def _norm_str(v) -> Optional[str]:
                if v is None:
                    return None
                if isinstance(v, str):
                    s = v.strip()
                    return s if s else None
                return str(v).strip() or None

            def _split_name(full_name: Optional[str]) -> tuple[Optional[str], Optional[str]]:
                if not full_name:
                    return None, None
                name = full_name.strip()
                if not name or name == "Unknown":
                    return None, None

                # Handle "Last, First ..." format
                if "," in name:
                    last, rest = name.split(",", 1)
                    last = last.strip() or None
                    first = rest.strip().split(" ")[0] if rest.strip() else None
                    return first, last

                parts = [p for p in name.split() if p]
                if len(parts) == 1:
                    return parts[0], None
                return parts[0], parts[-1]
            
            # Create ApplicationData object
            state_value = json_data.get('state')
            # Convert null/None to None, keep valid state values
            if state_value in [None, 'null', 'None', '']:
                state_value = None
            elif state_value == 'Unknown':
                state_value = 'Unknown'

            first_name = _norm_str(json_data.get("first_name")) or None
            last_name = _norm_str(json_data.get("last_name")) or None
            full_name = _norm_str(json_data.get("name")) or "Unknown"

            # If split names missing but full name present, derive them
            if (not first_name or first_name == "Unknown") or (not last_name or last_name == "Unknown"):
                derived_first, derived_last = _split_name(full_name)
                if not first_name and derived_first:
                    first_name = derived_first
                if not last_name and derived_last:
                    last_name = derived_last

            # If full name missing but split present, construct it
            if (not full_name or full_name == "Unknown") and first_name:
                full_name = f"{first_name} {last_name}".strip() if last_name else first_name
            
            app_data = ApplicationData(
                wai_number=wai_number,
                first_name=first_name,
                last_name=last_name,
                name=full_name,
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


# Note: Application scoring is now handled by `agents.scoring_runner.ScoringRunner`.


# Made with Bob
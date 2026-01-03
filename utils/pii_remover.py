"""Utility for removing PII from text using Presidio.

This module provides functions to identify and remove personally identifiable
information from text content using Microsoft's Presidio library with enhanced
international phone number detection.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-05
Version: 2.1.0 (Added international phone number support)
License: MIT
"""

import logging
from typing import Tuple, List, Optional
import re

from presidio_analyzer import AnalyzerEngine, EntityRecognizer, RecognizerResult
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig

logger = logging.getLogger()

# Global instances (initialized once)
_analyzer = None
_anonymizer = None


class InternationalPhoneRecognizer(EntityRecognizer):
    """Custom recognizer for international phone numbers.
    
    Detects phone numbers in various international formats including:
    - E.164 format: +1234567890
    - With country code: +1 (555) 123-4567
    - International format: +44 20 7123 4567
    - Various separators: spaces, dashes, dots, parentheses
    """
    
    # Comprehensive regex for international phone numbers
    PATTERNS = [
        # E.164 format: +1234567890 (7-15 digits)
        r'\+\d{1,4}\d{7,14}',
        # With separators: +1 (555) 123-4567, +44 20 7123 4567
        r'\+\d{1,4}[\s\-\.]?\(?\d{1,4}\)?[\s\-\.]?\d{1,4}[\s\-\.]?\d{1,9}',
        # Country code with parentheses: (+1) 555-123-4567
        r'\(\+\d{1,4}\)[\s\-\.]?\d{1,4}[\s\-\.]?\d{1,4}[\s\-\.]?\d{1,9}',
        # Without + but with country code: 001 555 123 4567
        r'\b00\d{1,3}[\s\-\.]?\d{1,4}[\s\-\.]?\d{1,4}[\s\-\.]?\d{1,9}\b',
    ]
    
    def __init__(self):
        super().__init__(
            supported_entities=["PHONE_NUMBER"],
            supported_language="en",
            name="International Phone Recognizer"
        )
        self.compiled_patterns = [re.compile(pattern) for pattern in self.PATTERNS]
    
    def load(self) -> None:
        """Load the recognizer - no external resources needed."""
        pass
    
    def analyze(self, text: str, entities: List[str], nlp_artifacts=None) -> List[RecognizerResult]:
        """Analyze text for international phone numbers.
        
        Args:
            text: Text to analyze
            entities: List of entities to look for
            nlp_artifacts: NLP artifacts (not used)
            
        Returns:
            List of RecognizerResult objects for detected phone numbers
        """
        results = []
        
        if "PHONE_NUMBER" not in entities:
            return results
        
        # Search for each pattern
        for pattern in self.compiled_patterns:
            for match in pattern.finditer(text):
                # Validate the match (basic checks)
                phone_text = match.group()
                if self._is_valid_phone(phone_text):
                    results.append(
                        RecognizerResult(
                            entity_type="PHONE_NUMBER",
                            start=match.start(),
                            end=match.end(),
                            score=0.85  # High confidence for pattern match
                        )
                    )
        
        return results
    
    def _is_valid_phone(self, phone: str) -> bool:
        """Basic validation for phone number.
        
        Args:
            phone: Phone number string to validate
            
        Returns:
            True if phone number appears valid
        """
        # Remove all non-digit characters except +
        digits = re.sub(r'[^\d+]', '', phone)
        
        # Must have at least 7 digits (minimum valid phone number)
        digit_count = len(digits.replace('+', ''))
        if digit_count < 7:
            return False
        
        # Must not have too many digits (max 15 for E.164)
        if digit_count > 15:
            return False
        
        # If starts with +, must have country code (1-4 digits after +)
        if phone.startswith('+'):
            country_code_match = re.match(r'\+(\d{1,4})', phone)
            if not country_code_match:
                return False
        
        return True


def get_analyzer() -> AnalyzerEngine:
    """Get or create the Presidio analyzer instance with custom recognizers.
    
    Returns:
        AnalyzerEngine: Singleton analyzer instance with English-only support
            and international phone number detection.
    """
    global _analyzer
    if _analyzer is None:
        logger.info("Initializing Presidio AnalyzerEngine (English-only, one-time setup)")
        # Configure for English-only to avoid loading Spanish, Italian, Polish recognizers
        _analyzer = AnalyzerEngine(supported_languages=["en"])
        
        # Add custom international phone recognizer
        international_phone_recognizer = InternationalPhoneRecognizer()
        _analyzer.registry.add_recognizer(international_phone_recognizer)
        logger.info("Added InternationalPhoneRecognizer to Presidio")
    return _analyzer


def get_anonymizer() -> AnonymizerEngine:
    """Get or create the Presidio anonymizer instance.
    
    Returns:
        AnonymizerEngine: Singleton anonymizer instance.
    """
    global _anonymizer
    if _anonymizer is None:
        logger.info("Initializing Presidio AnonymizerEngine (one-time setup)")
        _anonymizer = AnonymizerEngine()
    return _anonymizer


def remove_pii(
    text: str,
    language: str = "en",
    score_threshold: float = 0.5,
    exclude_entities: Optional[List[str]] = None
) -> Tuple[str, List[str]]:
    """Remove PII from text using Presidio.
    
    Uses Microsoft's Presidio library to identify and redact personally
    identifiable information from the provided text. Returns the redacted
    text and a list of PII types that were found.
    
    Args:
        text (str): The text content to redact PII from.
        language (str): Language code for analysis. Defaults to "en".
        score_threshold (float): Minimum confidence score for PII detection.
            Defaults to 0.5 (50% confidence).
        exclude_entities (Optional[List[str]]): List of entity types to exclude
            from redaction. Defaults to ["PERSON", "LOCATION", "NRP"] to preserve
            names and locations.
    
    Returns:
        Tuple[str, List[str]]: A tuple containing:
            - redacted_text (str): Text with PII removed/replaced
            - pii_types_found (List[str]): List of PII types detected
    
    Example:
        >>> text = "John Smith lives at 123 Main St. Email: john@example.com"
        >>> redacted, pii_types = remove_pii(text)
        >>> print(redacted)
        John Smith lives at 123 Main St. Email: <EMAIL_ADDRESS>
        >>> print(pii_types)
        ['EMAIL_ADDRESS']
    
    Note:
        - By default, preserves names (PERSON) and locations (LOCATION)
        - Redacts: emails, phones, SSN, credit cards, URLs, dates, etc.
        - Uses spaCy NER model for entity recognition
        - Replaces PII with entity type placeholders (e.g., <EMAIL_ADDRESS>)
    """
    # Default: exclude names and locations from redaction
    if exclude_entities is None:
        exclude_entities = ["PERSON", "LOCATION", "NRP"]
    try:
        # Get analyzer and anonymizer instances
        analyzer = get_analyzer()
        anonymizer = get_anonymizer()
        
        logger.debug(f"Analyzing text for PII ({len(text)} chars)")
        
        # Analyze text for PII
        results = analyzer.analyze(
            text=text,
            language=language,
            score_threshold=score_threshold
        )
        
        if not results:
            logger.info("No PII detected in text")
            return text, []
        
        # Filter out excluded entity types
        filtered_results = [r for r in results if r.entity_type not in exclude_entities]
        
        if not filtered_results:
            logger.info(f"PII detected but all types excluded: {', '.join(set([r.entity_type for r in results]))}")
            return text, []
        
        # Extract unique PII types found (after filtering)
        pii_types = list(set([result.entity_type for result in filtered_results]))
        logger.info(f"Detected PII types to redact: {', '.join(pii_types)}")
        
        # Define anonymization operators (replace with entity type)
        operators = {}
        for entity_type in pii_types:
            operators[entity_type] = OperatorConfig("replace", {"new_value": f"<{entity_type}>"})
        
        # Anonymize the text (only filtered results)
        anonymized_result = anonymizer.anonymize(
            text=text,
            analyzer_results=filtered_results,
            operators=operators
        )
        
        redacted_text = anonymized_result.text
        
        logger.info(f"Redacted {len(filtered_results)} PII entities (excluded {len(results) - len(filtered_results)} entities)")
        logger.debug(f"Original length: {len(text)}, Redacted length: {len(redacted_text)}")
        
        return redacted_text, pii_types
        
    except Exception as e:
        logger.error(f"Error removing PII with Presidio: {str(e)}")
        # Return original text if redaction fails
        return text, []


def remove_pii_with_retry(
    text: str,
    model: Optional[str] = None,
    fallback_model: Optional[str] = None,
    max_retries: int = 2
) -> Tuple[str, List[str]]:
    """Remove PII with retry logic (compatibility wrapper).
    
    This function maintains compatibility with the LLM-based interface
    but uses Presidio for PII removal. The model parameters are ignored
    since Presidio doesn't use LLMs.
    
    Args:
        text (str): The text content to redact PII from.
        model (Optional[str]): Ignored (for compatibility).
        fallback_model (Optional[str]): Ignored (for compatibility).
        max_retries (int): Number of retry attempts. Defaults to 2.
    
    Returns:
        Tuple[str, List[str]]: Redacted text and list of PII types found.
    
    Example:
        >>> text = "Contact John Smith at john@example.com"
        >>> redacted, types = remove_pii_with_retry(text)
        >>> print(redacted)
        Contact <PERSON> at <EMAIL_ADDRESS>
    
    Note:
        - Presidio is deterministic, so retries use different thresholds
        - First attempt: 0.5 threshold (balanced)
        - Retry attempts: 0.3 threshold (more sensitive)
    """
    # Try with standard threshold
    for attempt in range(1, max_retries + 1):
        # Use lower threshold on retries to catch more PII
        threshold = 0.5 if attempt == 1 else 0.3
        
        if attempt > 1:
            logger.info(f"PII removal retry attempt {attempt}/{max_retries} with threshold: {threshold}")
        
        redacted_text, pii_types = remove_pii(text, score_threshold=threshold)
        
        # Check if redaction was successful (PII found)
        if pii_types:
            return redacted_text, pii_types
    
    logger.info("No PII detected after all attempts")
    return text, []


def get_supported_entities() -> List[str]:
    """Get list of PII entity types supported by Presidio.
    
    Returns:
        List[str]: List of supported entity type names.
    
    Example:
        >>> entities = get_supported_entities()
        >>> print(entities)
        ['PERSON', 'EMAIL_ADDRESS', 'PHONE_NUMBER', 'CREDIT_CARD', ...]
    """
    analyzer = get_analyzer()
    return analyzer.get_supported_entities()

# Made with Bob

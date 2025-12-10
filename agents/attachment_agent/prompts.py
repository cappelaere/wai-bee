"""Prompts for PII removal using LLM.

This module contains system prompts and prompt generation functions for
identifying and removing personally identifiable information (PII) from text.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-05
Version: 1.0.0
License: MIT
"""

# System prompt for PII redaction
SYSTEM_PROMPT = """You are a PII (Personally Identifiable Information) redaction specialist. Your task is to identify and remove all personally identifiable information from text while preserving the document's meaning, structure, and readability.

You must redact the following types of PII:
- Full names (first, middle, last names)
- Email addresses
- Phone numbers (all formats)
- Physical addresses (street, city, state, zip)
- Social Security Numbers (SSN)
- Dates of birth
- Driver's license numbers
- Passport numbers
- Account numbers
- Credit card numbers
- Medical record numbers
- Any other unique identifiers

IMPORTANT RULES:
1. Replace PII with generic placeholders in [BRACKETS]:
   - Names: [NAME], [FIRST_NAME], [LAST_NAME]
   - Emails: [EMAIL]
   - Phones: [PHONE]
   - Addresses: [ADDRESS], [CITY], [STATE], [ZIP]
   - SSN: [SSN]
   - Dates of birth: [DOB]
   - Other IDs: [ID_NUMBER]

2. Preserve document structure, formatting, and non-PII content
3. Keep professional titles, job positions, and organization names
4. Keep dates that are not dates of birth
5. Keep general location references (e.g., "Phoenix area" is OK, but "123 Main St, Phoenix" is not)

Return ONLY the redacted text. Do not include explanations or metadata."""


def get_pii_removal_prompt(text: str) -> str:
    """Generate prompt for PII removal from text.
    
    Creates a user prompt that includes the text to be redacted and
    instructions for the LLM to remove PII.
    
    Args:
        text (str): The text content to redact PII from.
    
    Returns:
        str: Formatted prompt for the LLM.
    
    Example:
        >>> text = "John Smith lives at 123 Main St. Email: john@example.com"
        >>> prompt = get_pii_removal_prompt(text)
        >>> # LLM will return: "[NAME] lives at [ADDRESS]. Email: [EMAIL]"
    
    Note:
        The prompt instructs the LLM to return only the redacted text
        without any additional commentary or metadata.
    """
    return f"""Please redact all PII from the following text. Return ONLY the redacted text with PII replaced by appropriate placeholders.

TEXT TO REDACT:
{text}

REDACTED TEXT:"""


def extract_pii_types(original_text: str, redacted_text: str) -> list[str]:
    """Extract types of PII that were found and redacted.
    
    Analyzes the redacted text to identify which types of PII placeholders
    were used, indicating what types of PII were found in the original text.
    
    Args:
        original_text (str): Original text before redaction.
        redacted_text (str): Text after PII redaction.
    
    Returns:
        list[str]: List of PII types found (e.g., ["names", "emails", "phones"]).
    
    Example:
        >>> original = "Contact John at john@example.com or 555-1234"
        >>> redacted = "Contact [NAME] at [EMAIL] or [PHONE]"
        >>> types = extract_pii_types(original, redacted)
        >>> print(types)
        ['names', 'emails', 'phones']
    
    Note:
        Returns empty list if no PII was detected or if redaction failed.
    """
    pii_types = []
    
    # Check for each type of PII placeholder
    if '[NAME]' in redacted_text or '[FIRST_NAME]' in redacted_text or '[LAST_NAME]' in redacted_text:
        pii_types.append('names')
    
    if '[EMAIL]' in redacted_text:
        pii_types.append('emails')
    
    if '[PHONE]' in redacted_text:
        pii_types.append('phones')
    
    if '[ADDRESS]' in redacted_text or '[CITY]' in redacted_text or '[STATE]' in redacted_text or '[ZIP]' in redacted_text:
        pii_types.append('addresses')
    
    if '[SSN]' in redacted_text:
        pii_types.append('ssn')
    
    if '[DOB]' in redacted_text:
        pii_types.append('date_of_birth')
    
    if '[ID_NUMBER]' in redacted_text:
        pii_types.append('id_numbers')
    
    return pii_types

# Made with Bob

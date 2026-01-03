"""Prompts for the Application Agent.

This module contains the system and user prompts used by the Application Agent
for extracting information from scholarship application documents using LLM.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-05
Version: 1.0.0
License: MIT

Constants:
    SYSTEM_PROMPT: System prompt defining the agent's role and guidelines.
    USER_PROMPT_TEMPLATE: Template for user prompts with document content.

Functions:
    get_extraction_prompt: Generate formatted extraction prompt.

Example:
    >>> from agents.application_agent.prompts import get_extraction_prompt
    >>>
    >>> document_text = "Application for John Doe from Boston, USA..."
    >>> prompt = get_extraction_prompt(document_text)
"""

SYSTEM_PROMPT = """You are an expert at extracting information from scholarship application documents.

Your task is to carefully read the application document and extract the following information:
1. Applicant's first name
2. Applicant's last name
3. Applicant's full name (optional but recommended)
2. City of residence
3. State of residence (for US applicants only)
4. Country of residence

IMPORTANT - Standardization Requirements:
- Extract the exact name as it appears in the document
- For US states: MUST use the two-letter postal abbreviation (e.g., "NY", "CA", "TX", "AZ", "FL")
- For countries: MUST use the official English country name (e.g., "United States", "United Kingdom", "Canada")
  * Use "United States" (not "USA", "US", or "America")
  * Use "United Kingdom" (not "UK" or "Great Britain")
- For cities: Use proper capitalization and standard spelling
- If the applicant is not from the United States, set state to null
- If information is not clearly stated, use "Unknown" as the value
- Be precise and accurate in your extraction
- Look for sections like "Personal Information", "Contact Details", "Applicant Information", etc.
"""

USER_PROMPT_TEMPLATE = """Please extract the applicant's first name, last name, city, state (if in US), and country from the following scholarship application document.

Document content:
{document_text}

Provide the extracted information in the following JSON format:
{{
  "first_name": "First Name",
  "last_name": "Last Name",
  "name": "Full Name (optional but recommended)",
  "city": "City Name",
  "state": "Two-letter state code or null",
  "country": "Official English Country Name"
}}

CRITICAL FORMATTING RULES:
- State: MUST be two-letter postal code (NY, CA, TX, AZ, FL, etc.) for US applicants, null for others
- Country: MUST use official English name:
  * "United States" (not USA, US, or America)
  * "United Kingdom" (not UK)
  * "Canada", "Mexico", "India", "China", etc.
- If any information is not found, use "Unknown" as the value
"""


def get_extraction_prompt(document_text: str) -> str:
    """Generate the user prompt for extraction.
    
    Creates a formatted prompt by inserting the document text into the
    user prompt template.
    
    Args:
        document_text (str): The parsed text content from the application
            document.
    
    Returns:
        str: Formatted prompt string ready to send to the LLM.
    
    Example:
        >>> doc_text = "Applicant: John Doe, City: Boston, Country: USA"
        >>> prompt = get_extraction_prompt(doc_text)
        >>> "John Doe" in prompt
        True
    """
    return USER_PROMPT_TEMPLATE.format(document_text=document_text)


# Note:
# Application scoring prompts are generated per-scholarship in data/<scholarship>/prompts/
# and loaded via utils.prompt_loader. This module is now extraction-only.


# Made with Bob

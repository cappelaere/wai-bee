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
1. Applicant's full name
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

USER_PROMPT_TEMPLATE = """Please extract the applicant's name, city, state (if in US), and country from the following scholarship application document.

Document content:
{document_text}

Provide the extracted information in the following JSON format:
{{
  "name": "Full Name",
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


# Application Scoring Prompts

SCORING_SYSTEM_PROMPT = """You are an expert at evaluating scholarship application completeness and validity.

Your task is to assess the quality of the application based on:
1. COMPLETENESS: Are all required fields filled out?
2. VALIDITY: Is the data valid and properly formatted?
3. ATTACHMENTS: Are required attachments present?

You will be provided with:
- Extracted applicant information (name, city, state, country)
- List of attachment files found
- Scoring criteria

Evaluate objectively and provide scores with clear reasoning."""

SCORING_USER_PROMPT_TEMPLATE = """Please evaluate this scholarship application for completeness and validity.

IMPORTANT: The information below has been SUCCESSFULLY EXTRACTED from the application.
Do NOT say any of this information is "missing" - it is all present and extracted.

EXTRACTED APPLICANT INFORMATION (ALL PRESENT):
✓ Name: {name}
✓ City: {city}
✓ State: {state} (Note: State is only required for US applicants. N/A for non-US is correct.)
✓ Country: {country}

ATTACHMENT FILES FOUND ({attachment_count} files):
{attachment_list}

CRITICAL: The above are FILENAMES, not labels or descriptions.
- Filenames like "75179_19_8.pdf" are standard system-generated names
- Do NOT evaluate filenames as if they were labels or descriptions
- Do NOT comment on "unclear labels" - we only track filenames, not labels
- Do NOT deduct points because filenames are not descriptive

SCORING CRITERIA:
{criteria}

EVALUATION INSTRUCTIONS:
1. COMPLETENESS (0-30): All required fields above are present. Score based on data quality, not presence.
   - For non-US applicants, "N/A" or null state is CORRECT and should NOT be penalized
2. VALIDITY (0-30): Evaluate if the data format and values are valid and properly formatted.
   - State should only be validated for US applicants
3. ATTACHMENTS (0-40): Score based on the number and validity of attachment files found.
   - Only evaluate based on the filenames provided above
   - Do NOT comment on missing labels, descriptions, or other metadata

DO NOT deduct points for:
- "Missing" information that is clearly shown above
- State being N/A for non-US applicants (this is correct)
- Missing labels or metadata for attachments (we only track filenames)

Focus on DATA QUALITY, not data presence.
Only evaluate what IS provided, not what you think should be provided.

Provide your evaluation in the following JSON format:
{{
  "summary": "Brief summary of application quality",
  "scores": {{
    "completeness_score": 0-30,
    "validity_score": 0-30,
    "attachment_score": 0-40,
    "overall_score": 0-100
  }},
  "score_breakdown": {{
    "completeness_reasoning": "Explanation of completeness score based on data quality",
    "validity_reasoning": "Explanation of validity score based on format and values",
    "attachment_reasoning": "Explanation of attachment score based on files found"
  }},
  "completeness_issues": ["list", "of", "quality", "issues"],
  "validity_issues": ["list", "of", "format", "issues"],
  "attachment_status": "Summary of attachment completeness"
}}

Be objective and evaluate based on what IS present, not what you think might be missing."""


def get_scoring_prompt(
    name: str,
    city: str,
    state: str,
    country: str,
    attachment_files: list[str],
    criteria: str
) -> str:
    """Generate the user prompt for application scoring.
    
    Args:
        name: Applicant's name.
        city: Applicant's city.
        state: Applicant's state (or "None" if not US).
        country: Applicant's country.
        attachment_files: List of attachment file names found.
        criteria: Scoring criteria text.
    
    Returns:
        Formatted scoring prompt string.
    """
    # Format attachment list with count
    attachment_count = len(attachment_files)
    if attachment_files:
        attachment_list = "\n".join(f"- {f}" for f in attachment_files)
    else:
        attachment_list = "No attachments found"
    
    # Format state display
    state_display = state if state else "N/A (non-US applicant)"
    
    return SCORING_USER_PROMPT_TEMPLATE.format(
        name=name,
        city=city,
        state=state_display,
        country=country,
        attachment_count=attachment_count,
        attachment_list=attachment_list,
        criteria=criteria
    )


# Made with Bob

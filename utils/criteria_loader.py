"""Utility for loading scholarship evaluation criteria/prompts.

This module provides functions to load scholarship-specific criteria/prompt files
that guide the LLM's analysis. Supports both old (criteria/) and new (prompts/) formats.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-05
Version: 1.1.0
License: MIT
"""

import logging
from pathlib import Path
from functools import lru_cache

logger = logging.getLogger()


# Cache for loaded criteria to avoid repeated file reads
_criteria_cache = {}


def load_criteria(scholarship_folder: Path, criteria_type: str = "recommendation") -> str:
    """Load evaluation criteria/prompt from scholarship folder.
    
    Checks both new and legacy locations:
    - New: {scholarship_folder}/prompts/{criteria_type}_analysis.txt
    - Legacy: {scholarship_folder}/criteria/{criteria_type}_criteria.txt
    
    Args:
        scholarship_folder: Path to scholarship folder (e.g., "data/Delaney_Wings").
        criteria_type: Type of criteria to load (default: "recommendation").
    
    Returns:
        Criteria text as string. Returns default criteria if file not found.
    
    Example:
        >>> scholarship_folder = Path("data/Delaney_Wings")
        >>> criteria = load_criteria(scholarship_folder, "recommendation")
        >>> print(len(criteria))
        3245
    
    Note:
        - Prefers new prompts/ format over legacy criteria/ format
        - Falls back to default criteria if file doesn't exist
    """
    # Handle both "Applications" subfolder and direct scholarship folder
    if scholarship_folder.name == "Applications":
        scholarship_folder = scholarship_folder.parent
    
    # Try new format first: prompts/{type}_analysis.txt
    new_format_file = scholarship_folder / "prompts" / f"{criteria_type}_analysis.txt"
    # Legacy format: criteria/{type}_criteria.txt
    legacy_format_file = scholarship_folder / "criteria" / f"{criteria_type}_criteria.txt"
    
    # Determine which file to use
    if new_format_file.exists():
        criteria_file = new_format_file
    elif legacy_format_file.exists():
        criteria_file = legacy_format_file
    else:
        logger.warning(f"No prompt/criteria file found for {criteria_type}")
        logger.warning(f"  Checked: {new_format_file}")
        logger.warning(f"  Checked: {legacy_format_file}")
        logger.warning("Using default recommendation criteria")
        return get_default_criteria()
    
    # Check cache first
    cache_key = str(criteria_file)
    if cache_key in _criteria_cache:
        logger.debug(f"Using cached criteria for: {criteria_file}")
        return _criteria_cache[cache_key]
    
    # Load from file
    try:
        with open(criteria_file, 'r', encoding='utf-8') as f:
            criteria = f.read()
        logger.info(f"Loaded criteria from: {criteria_file}")
        # Cache the loaded criteria
        _criteria_cache[cache_key] = criteria
        return criteria
    except Exception as e:
        logger.error(f"Error reading criteria file {criteria_file}: {str(e)}")
        logger.warning("Falling back to default criteria")
        default = get_default_criteria()
        _criteria_cache[cache_key] = default
        return default


def get_default_criteria() -> str:
    """Return default recommendation evaluation criteria.
    
    Used as fallback when scholarship-specific criteria file is not found.
    
    Returns:
        Default criteria text as string.
    
    Example:
        >>> criteria = get_default_criteria()
        >>> print("Recommender Credibility" in criteria)
        True
    """
    return """# Default Recommendation Evaluation Criteria

## Evaluation Focus Areas

1. **Recommender Credibility and Relationship**
   - Assess the recommender's qualifications and relationship to the applicant
   - Consider the duration and depth of the relationship
   - Evaluate the recommender's ability to assess the applicant's qualifications

2. **Specific Examples and Evidence**
   - Look for concrete examples of the applicant's skills and achievements
   - Value specific anecdotes over generic praise
   - Assess the depth of knowledge demonstrated about the applicant

3. **Character and Professional Qualities**
   - Look for evidence of reliability, responsibility, and professionalism
   - Value mentions of leadership, teamwork, and communication skills
   - Consider endorsements of work ethic and dedication
   - Assess ability to learn and adapt

4. **Consistency and Depth**
   - Value consistency in themes across multiple recommendations
   - Look for specific examples rather than generic statements
   - Consider the depth of knowledge the recommender demonstrates
   - Assess whether recommendations provide concrete evidence

## Scoring Guidelines

- **Average Support Strength (0-100)**: Reflects both positivity and specificity of endorsements
- **Consistency Score (0-100)**: Rewards alignment across multiple recommendations
- **Depth of Endorsement (0-100)**: Emphasizes specific examples and detailed observations
- **Overall Score (0-100)**: Considers both individual letter quality and aggregate strength

## Key Factors

- Recommendations should provide specific examples and concrete evidence
- Generic recommendations should be scored lower
- Consistency across multiple letters indicates stronger support
- Depth of relationship and knowledge should be considered
"""


def get_criteria_path(scholarship_folder: Path, criteria_type: str = "recommendation") -> Path:
    """Get the path to a criteria/prompt file.
    
    Returns the path to the file that exists, preferring new format over legacy.
    
    Args:
        scholarship_folder: Path to scholarship folder.
        criteria_type: Type of criteria (default: "recommendation").
    
    Returns:
        Path object for the criteria file.
    
    Example:
        >>> scholarship_folder = Path("data/Delaney_Wings")
        >>> path = get_criteria_path(scholarship_folder, "recommendation")
        >>> print(path)
        data/Delaney_Wings/prompts/recommendation_analysis.txt
    """
    # Handle both "Applications" subfolder and direct scholarship folder
    if scholarship_folder.name == "Applications":
        scholarship_folder = scholarship_folder.parent
    
    # Try new format first
    new_format_path = scholarship_folder / "prompts" / f"{criteria_type}_analysis.txt"
    if new_format_path.exists():
        return new_format_path
    
    # Fall back to legacy format
    return scholarship_folder / "criteria" / f"{criteria_type}_criteria.txt"


def validate_criteria(criteria: str) -> tuple[bool, str]:
    """Validate that criteria text is suitable for analysis.
    
    Args:
        criteria: Criteria text to validate.
    
    Returns:
        Tuple of (is_valid, error_message).
        If valid, error_message is empty string.
    
    Example:
        >>> criteria = load_criteria(Path("data/Delaney_Wings"))
        >>> is_valid, error = validate_criteria(criteria)
        >>> print(is_valid)
        True
    """
    if not criteria or len(criteria.strip()) == 0:
        return False, "Criteria text is empty"
    
    if len(criteria) < 100:
        return False, "Criteria text is too short (< 100 characters)"
    
    # Check for key sections (flexible matching)
    key_terms = ["evaluation", "criteria", "score", "assess"]
    has_key_term = any(term.lower() in criteria.lower() for term in key_terms)
    
    if not has_key_term:
        return False, "Criteria text doesn't appear to contain evaluation guidance"
    
    return True, ""


def clear_criteria_cache():
    """Clear the criteria cache.
    
    Useful for testing or when criteria files are updated at runtime.
    
    Example:
        >>> clear_criteria_cache()
        >>> # Criteria will be reloaded on next access
    """
    global _criteria_cache
    _criteria_cache.clear()
    logger.info("Criteria cache cleared")


# Made with Bob
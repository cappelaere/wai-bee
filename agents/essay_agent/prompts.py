"""Prompts for Essay Agent.

This module contains prompt templates for analyzing personal essays
and extracting motivation, goals, character traits, and leadership qualities.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-06
Version: 1.0.0
License: MIT
"""


def build_essay_analysis_prompt(essay_texts: list[str], criteria: str) -> str:
    """Build prompt for analyzing personal essays.
    
    Args:
        essay_texts: List of essay text content (1-2 essays).
        criteria: Evaluation criteria text.
        
    Returns:
        Formatted prompt for LLM analysis.
    """
    # Combine essays with clear separation
    combined_essays = "\n\n=== ESSAY SEPARATOR ===\n\n".join(essay_texts)
    
    prompt = f"""You are an expert scholarship evaluator analyzing personal essays for the Women in Aviation International (WAI) scholarship program.

EVALUATION CRITERIA:
{criteria}

PERSONAL ESSAYS TO ANALYZE:
{combined_essays}

Your task is to analyze these personal essays and extract key information about the applicant's:
1. Aviation passion and motivation
2. Career goals and clarity of vision
3. Personal character traits (persistence, resilience, determination, adaptability)
4. Leadership roles and community service
5. Alignment with WAI values
6. Unique strengths and qualities

SCORING GUIDELINES:
- motivation_score (0-100): Assess passion for aviation, commitment to the field, and genuine interest
- goals_clarity_score (0-100): Evaluate clarity of career goals, realistic planning, and vision
- character_service_leadership_score (0-100): Assess character traits, community involvement, and leadership
- overall_score (0-100): Holistic assessment of personal profile

Provide detailed reasoning for each score in the score_breakdown section.

You MUST respond with ONLY valid JSON matching this exact structure:

{{
  "summary": "Brief executive summary of the applicant's personal profile and key strengths",
  "profile_features": {{
    "motivation_summary": "Summary of applicant's motivation for pursuing aviation",
    "career_goals_summary": "Summary of career goals and aspirations",
    "aviation_path_stage": "Current stage in aviation journey (e.g., 'Beginning flight training', 'Pursuing commercial rating', 'Early career professional')",
    "community_service_summary": "Summary of community involvement and service activities",
    "leadership_roles": ["List of leadership positions or roles held"],
    "personal_character_indicators": ["List of character traits demonstrated (e.g., 'resilience', 'determination', 'adaptability')"],
    "alignment_with_wai": "How well the applicant aligns with WAI values and mission",
    "unique_strengths": ["List of unique strengths, experiences, or qualities"]
  }},
  "scores": {{
    "motivation_score": 85,
    "goals_clarity_score": 80,
    "character_service_leadership_score": 90,
    "overall_score": 85
  }},
  "score_breakdown": {{
    "motivation_score_reasoning": "Detailed explanation for motivation score",
    "goals_clarity_score_reasoning": "Detailed explanation for goals clarity score",
    "character_service_leadership_score_reasoning": "Detailed explanation for character/service/leadership score",
    "overall_score_reasoning": "Detailed explanation for overall score"
  }}
}}

IMPORTANT: 
- Respond with ONLY the JSON object, no additional text
- All scores must be integers between 0 and 100
- Provide specific evidence from the essays in your reasoning
- Be objective and fair in your assessment
- Consider both essays together when forming your evaluation"""

    return prompt


def build_retry_prompt(original_response: str, error_message: str) -> str:
    """Build prompt for retry after JSON parsing failure.
    
    Args:
        original_response: The original LLM response that failed.
        error_message: The error message from parsing attempt.
        
    Returns:
        Formatted retry prompt.
    """
    prompt = f"""Your previous response could not be parsed as valid JSON.

ERROR: {error_message}

PREVIOUS RESPONSE:
{original_response}

Please provide a corrected response with ONLY valid JSON matching the required structure.
Do not include any explanatory text, markdown formatting, or code blocks.
Start directly with the opening brace {{ and end with the closing brace }}.

Required JSON structure:
{{
  "summary": "string",
  "profile_features": {{
    "motivation_summary": "string",
    "career_goals_summary": "string",
    "aviation_path_stage": "string",
    "community_service_summary": "string",
    "leadership_roles": ["string"],
    "personal_character_indicators": ["string"],
    "alignment_with_wai": "string",
    "unique_strengths": ["string"]
  }},
  "scores": {{
    "motivation_score": 0,
    "goals_clarity_score": 0,
    "character_service_leadership_score": 0,
    "overall_score": 0
  }},
  "score_breakdown": {{
    "motivation_score_reasoning": "string",
    "goals_clarity_score_reasoning": "string",
    "character_service_leadership_score_reasoning": "string",
    "overall_score_reasoning": "string"
  }}
}}"""

    return prompt

# Made with Bob

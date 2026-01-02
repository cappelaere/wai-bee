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
- motivation_score (0-10): Assess passion for aviation, commitment to the field, and genuine interest
- goals_clarity_score (0-10): Evaluate clarity of career goals, realistic planning, and vision
- character_service_leadership_score (0-10): Assess character traits, community involvement, and leadership
- overall_score (0-10): Holistic assessment of personal profile

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
    "motivation_score": 8,
    "goals_clarity_score": 8,
    "character_service_leadership_score": 9
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


# Note: Repair prompts are now generated and loaded from agents.json via utils.prompt_loader.
# The build_retry_prompt function was removed as it is no longer used.

# Made with Bob

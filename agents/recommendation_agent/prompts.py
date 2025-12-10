"""Prompts for recommendation letter analysis.

This module contains the system prompt and prompt builder functions for
analyzing recommendation letters using LLM.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-05
Version: 2.0.0
License: MIT
"""

SYSTEM_PROMPT = """You are an expert scholarship evaluator specializing in analyzing recommendation letters for aviation scholarships. Your role is to:

1. Carefully read and analyze recommendation letters
2. Extract key information about the recommender and their relationship to the applicant
3. Identify specific strengths, examples, and potential concerns mentioned
4. Assess the overall quality and depth of support provided
5. Generate consistent, objective scores based on provided criteria
6. Provide detailed reasoning for all scores and assessments

You must be thorough, objective, and consistent in your evaluations. Focus on:
- Specific examples and concrete evidence over generic praise
- The recommender's credibility and relationship depth
- Consistency of themes across multiple recommendations
- The depth and specificity of endorsements

Always provide your analysis in valid JSON format matching the provided schema exactly."""


def build_analysis_prompt(
    recommendation_texts: list[str],
    criteria: str
) -> str:
    """Build the analysis prompt for LLM.
    
    Includes:
    - Recommendation texts
    - Evaluation criteria
    - JSON structure requirements
    - Output format instructions
    
    Args:
        recommendation_texts: List of recommendation letter texts.
        criteria: Evaluation criteria text.
    
    Returns:
        Complete prompt string for LLM.
    
    Example:
        >>> texts = ["Letter 1 content...", "Letter 2 content..."]
        >>> criteria = "Evaluate based on..."
        >>> prompt = build_analysis_prompt(texts, criteria)
    """
    # Format recommendation texts
    recommendations_section = ""
    if recommendation_texts:
        recommendations_section = "\n\nRecommendation Letters:\n"
        for i, text in enumerate(recommendation_texts, 1):
            # Limit each letter to 3000 characters to avoid token limits
            recommendations_section += f"\nRecommendation Letter {i}:\n{text[:3000]}\n"
    else:
        recommendations_section = "\n\nNo recommendation letters found."
    
    # Add criteria section
    criteria_section = ""
    if criteria:
        criteria_section = f"""

Additional Scholarship-Specific Criteria:
{criteria}

Please take these additional criteria into account when analyzing the recommendations and scoring.
"""
    
    # Build the complete prompt
    prompt = f"""You are a Recommendation Profile Agent analyzing recommendation letters for a WAI (Women in Aviation International) scholarship applicant.

Your task is to analyze the recommendation letters to extract:
1. Recommender information (role, relationship to applicant, duration of relationship)
2. Key strengths and positive attributes mentioned
3. Specific examples or evidence provided
4. Potential concerns or areas for improvement (if any)
5. Overall strength and depth of support
6. Consistency across multiple recommendations (if applicable)

{recommendations_section}{criteria_section}

Based on the recommendation letters{', and the additional criteria provided above' if criteria else ''}, provide a JSON response with the following structure:

{{
    "summary": "A 1 paragraph summary (4-6 sentences) of the overall recommendation strength, key themes, and consistency across letters",
    "profile_features": {{
        "recommendations": [
            {{
                "recommender_role": "instructor|employer|mentor|colleague|other",
                "relationship_duration": "description of how long they've known the applicant",
                "key_strengths_mentioned": ["list of key strengths or positive attributes"],
                "specific_examples": ["specific examples or evidence provided"],
                "potential_concerns": ["any concerns or areas for improvement mentioned, or empty array if none"],
                "overall_tone": "very_positive|positive|neutral|mixed"
            }}
        ],
        "aggregate_analysis": {{
            "common_themes": ["themes that appear across multiple letters"],
            "strength_consistency": "high|medium|low",
            "depth_of_support": "deep|moderate|surface_level"
        }}
    }},
    "scores": {{
        "average_support_strength_score": <integer 0-100, required>,
        "consistency_of_support_score": <integer 0-100, required>,
        "depth_of_endorsement_score": <integer 0-100, required>,
        "overall_score": <integer 0-100, required>
    }},
    "score_breakdown": {{
        "average_support_strength_score_reasoning": "Explanation of average support strength score",
        "consistency_of_support_score_reasoning": "Explanation of consistency score",
        "depth_of_endorsement_score_reasoning": "Explanation of depth of endorsement score"
    }}
}}

CRITICAL JSON FORMAT REQUIREMENTS:
- You MUST respond with ONLY valid JSON
- Do NOT include markdown code blocks (```json or ```)
- Do NOT include any text before or after the JSON
- Do NOT include comments or explanations
- Do NOT use trailing commas
- Do NOT use single quotes (use double quotes only)
- All scores must be integers between 0 and 100
- The response must be parseable by json.loads() without any preprocessing"""

    return prompt


def build_retry_prompt(
    original_response: str,
    validation_errors: list[str]
) -> str:
    """Build a retry prompt when validation fails.
    
    Args:
        original_response: The LLM's original response that failed validation.
        validation_errors: List of validation error messages.
    
    Returns:
        Retry prompt string.
    
    Example:
        >>> original = '{"summary": "Good"}'  # Missing fields
        >>> errors = ["Missing required field: profile_features"]
        >>> retry_prompt = build_retry_prompt(original, errors)
    """
    errors_str = "\n".join(f"- {error}" for error in validation_errors)
    
    prompt = f"""Your previous response had validation errors. Please fix them and provide a corrected response.

VALIDATION ERRORS:
{errors_str}

YOUR PREVIOUS RESPONSE:
{original_response}

Please provide a corrected JSON response that:
1. Fixes all validation errors listed above
2. Includes all required fields
3. Uses correct data types
4. Follows the exact structure specified

CRITICAL: Respond with ONLY the corrected JSON object, no additional text, no markdown code blocks."""

    return prompt


# Made with Bob
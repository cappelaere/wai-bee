"""Prompts for Academic Agent LLM analysis.

This module contains system prompts and prompt builders for analyzing
academic profiles from resumes using LLM.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-05
Version: 1.0.0
License: MIT
"""

SYSTEM_PROMPT = """You are an expert academic evaluator specializing in aviation scholarship assessment. Your role is to analyze academic profiles from resumes and CVs to evaluate candidates' academic performance, program relevance, and readiness for aviation training or careers.

You have deep expertise in:
- Academic performance evaluation (GPA, honors, consistency)
- Aviation and STEM program assessment
- Academic trajectory analysis
- Readiness evaluation for aviation training
- Scholarship candidate evaluation

Your analysis must be thorough, evidence-based, and aligned with scholarship criteria."""


def build_analysis_prompt(resume_text: str, criteria: str) -> str:
    """Build prompt for academic profile analysis.
    
    Args:
        resume_text: Content of the resume/CV file.
        criteria: Academic evaluation criteria text.
    
    Returns:
        Complete prompt string for LLM analysis.
    
    Note:
        The JSON structure is embedded directly in the prompt for better
        model compliance, following the pattern from recommendation_agent.
    """
    
    # Limit resume text to prevent token overflow
    max_chars = 5000
    if len(resume_text) > max_chars:
        resume_text = resume_text[:max_chars] + "\n\n[Resume truncated for length]"
    
    prompt = f"""Analyze the following resume/CV and provide a comprehensive academic profile evaluation.

# RESUME/CV CONTENT

{resume_text}

# EVALUATION CRITERIA

{criteria}

# ANALYSIS INSTRUCTIONS

Based on the resume content and evaluation criteria, provide a detailed academic profile analysis. Extract all relevant academic information and evaluate the candidate's:

1. **Academic Performance**: GPA, grades, honors, academic standing, consistency
2. **Academic Relevance**: Program alignment with aviation/scholarship goals, relevant coursework
3. **Academic Readiness**: Preparedness for aviation training or advanced studies
4. **Academic Trajectory**: Growth, improvement, and academic development over time

# OUTPUT FORMAT

You MUST respond with ONLY a valid JSON object. Do NOT include markdown code blocks, explanations, or any text outside the JSON.

CRITICAL JSON FORMAT REQUIREMENTS:
- Return ONLY the JSON object
- Do NOT wrap in markdown code blocks (no ```json or ```)
- Do NOT add any explanatory text before or after the JSON
- Ensure all strings are properly escaped
- All scores must be integers between 0-100
- Use null for unknown values, not empty strings

Required JSON structure:

{{
  "summary": "Brief executive summary of the academic profile (2-3 sentences)",
  "profile_features": {{
    "current_school_name": "Name of current institution or null",
    "program": "Academic program/major or null",
    "education_level": "Bachelor's/Master's/PhD/etc. or null",
    "gpa": "GPA value as string or null",
    "academic_awards": ["Award 1", "Award 2"] or [],
    "relevant_courses": ["Course 1", "Course 2"] or [],
    "academic_trajectory": "Description of academic progress and trends or null",
    "strengths": ["Strength 1", "Strength 2"] or [],
    "areas_for_improvement": ["Area 1", "Area 2"] or []
  }},
  "scores": {{
    "academic_performance_score": 0-10,
    "academic_relevance_score": 0-10,
    "academic_readiness_score": 0-10,
  }},
  "score_breakdown": {{
    "academic_performance_score_reasoning": "Detailed explanation with specific evidence",
    "academic_relevance_score_reasoning": "Detailed explanation with specific evidence",
    "academic_readiness_score_reasoning": "Detailed explanation with specific evidence"
  }}
}}

SCORING GUIDELINES:
- 9-10: Exceptional - Outstanding academic record, highly relevant program, excellent readiness
- 8-9: Strong - Very good academic performance, relevant program, good readiness
- 7-8: Good - Solid academic record, some relevance, adequate readiness
- 6-7: Fair - Acceptable academic performance, limited relevance, developing readiness
- Below 5: Needs improvement - Weak academic record or poor fit

Provide your analysis as a JSON object following the exact structure above."""

    return prompt


# Note: Repair prompts are now generated and loaded from agents.json via utils.prompt_loader.
# The build_retry_prompt function was removed as it is no longer used.

# Made with Bob

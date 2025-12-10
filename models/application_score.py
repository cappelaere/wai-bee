"""Application scoring data model.

This module defines the Pydantic model for application completeness and validity scores.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-06
Version: 1.0.0
License: MIT
"""

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field


class ApplicationScores(BaseModel):
    """Scores for application completeness and validity.
    
    Attributes:
        completeness_score: Score for field completeness (0-30).
        validity_score: Score for data validity (0-30).
        attachment_score: Score for attachment completeness (0-40).
        overall_score: Total score (0-100).
    """
    completeness_score: int = Field(..., ge=0, le=30, description="Field completeness score")
    validity_score: int = Field(..., ge=0, le=30, description="Data validity score")
    attachment_score: int = Field(..., ge=0, le=40, description="Attachment completeness score")
    overall_score: int = Field(..., ge=0, le=100, description="Total application score")


class ApplicationScoreBreakdown(BaseModel):
    """Detailed reasoning for application scores.
    
    Attributes:
        completeness_reasoning: Explanation of completeness score.
        validity_reasoning: Explanation of validity score.
        attachment_reasoning: Explanation of attachment score.
    """
    completeness_reasoning: str = Field(..., description="Reasoning for completeness score")
    validity_reasoning: str = Field(..., description="Reasoning for validity score")
    attachment_reasoning: str = Field(..., description="Reasoning for attachment score")


class ApplicationAnalysis(BaseModel):
    """Complete application analysis with scores.
    
    This model represents the full analysis of an application's completeness
    and validity, including scores and detailed reasoning.
    
    Attributes:
        wai_number: WAI application number.
        summary: Brief summary of application quality.
        scores: Breakdown of scores by component.
        score_breakdown: Detailed reasoning for each score.
        completeness_issues: List of missing or incomplete fields.
        validity_issues: List of data validity concerns.
        attachment_status: Summary of attachment completeness.
        processed_date: When the analysis was performed.
        source_file: Source application file name.
        model_used: LLM model used for analysis.
        criteria_used: Path to criteria file used.
    """
    wai_number: str = Field(..., description="WAI application number")
    summary: str = Field(..., description="Summary of application quality")
    
    scores: ApplicationScores = Field(..., description="Score breakdown")
    score_breakdown: ApplicationScoreBreakdown = Field(..., description="Score reasoning")
    
    completeness_issues: list[str] = Field(default_factory=list, description="Missing/incomplete fields")
    validity_issues: list[str] = Field(default_factory=list, description="Data validity concerns")
    attachment_status: str = Field(..., description="Attachment completeness summary")
    
    processed_date: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Analysis timestamp"
    )
    source_file: str = Field(..., description="Source application file")
    model_used: str = Field(..., description="LLM model used")
    criteria_used: str = Field(..., description="Criteria file path")


# Made with Bob
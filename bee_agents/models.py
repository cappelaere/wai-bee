"""Pydantic models for API responses.

This module defines the data models used for API request/response validation.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-08
Version: 1.0.0
License: MIT
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ScoreResponse(BaseModel):
    """Response model for individual score."""
    wai_number: str = Field(..., description="WAI application number")
    name: Optional[str] = Field(None, description="Applicant name")
    city: Optional[str] = Field(None, description="Applicant city")
    state: Optional[str] = Field(None, description="Applicant state (US only)")
    country: Optional[str] = Field(None, description="Applicant country")
    overall_score: int = Field(..., description="Overall score (0-100)")
    completeness_score: int = Field(..., description="Completeness score (0-30)")
    validity_score: int = Field(..., description="Validity score (0-30)")
    attachment_score: int = Field(..., description="Attachment score (0-40)")
    summary: str = Field(..., description="Brief summary of application quality")


class TopScoresResponse(BaseModel):
    """Response model for top scores."""
    scholarship: str = Field(..., description="Scholarship name")
    total_applications: int = Field(..., description="Total number of applications")
    top_scores: List[ScoreResponse] = Field(..., description="List of top scoring applications")


class StatisticsResponse(BaseModel):
    """Response model for scholarship statistics."""
    scholarship: str = Field(..., description="Scholarship name")
    total_applications: int = Field(..., description="Total number of applications")
    average_score: float = Field(..., description="Average overall score")
    median_score: float = Field(..., description="Median overall score")
    min_score: int = Field(..., description="Minimum score")
    max_score: int = Field(..., description="Maximum score")
    score_distribution: Dict[str, int] = Field(..., description="Score ranges and counts")


class ApplicationAnalysisResponse(BaseModel):
    """Response model for application analysis."""
    wai_number: str = Field(..., description="WAI application number")
    summary: str = Field(..., description="Summary of application quality")
    scores: Dict[str, int] = Field(..., description="Score breakdown")
    score_breakdown: Dict[str, str] = Field(..., description="Detailed reasoning for scores")
    completeness_issues: List[str] = Field(..., description="List of completeness issues")
    validity_issues: List[str] = Field(..., description="List of validity issues")
    attachment_status: str = Field(..., description="Summary of attachment completeness")
    processed_date: str = Field(..., description="When the analysis was processed")
    source_file: str = Field(..., description="Source application file")


class AcademicAnalysisResponse(BaseModel):
    """Response model for academic analysis."""
    wai_number: str = Field(..., description="WAI application number")
    summary: str = Field(..., description="Summary of academic performance")
    profile_features: Dict[str, Any] = Field(..., description="Academic profile features")
    scores: Optional[Dict[str, int]] = Field(None, description="Academic scores")
    score_breakdown: Optional[Dict[str, str]] = Field(None, description="Score reasoning")
    processed_date: str = Field(..., description="When the analysis was processed")
    source_file: Optional[str] = Field(None, description="Source file")
    model_used: Optional[str] = Field(None, description="Model used for analysis")


class EssayAnalysisResponse(BaseModel):
    """Response model for essay analysis."""
    wai_number: str = Field(..., description="WAI application number")
    essay_number: int = Field(..., description="Essay number (1 or 2)")
    summary: str = Field(..., description="Summary of essay quality")
    strengths: List[str] = Field(..., description="Essay strengths")
    weaknesses: List[str] = Field(..., description="Essay weaknesses")
    score: Optional[int] = Field(None, description="Essay score if available")
    processed_date: str = Field(..., description="When the analysis was processed")


class RecommendationAnalysisResponse(BaseModel):
    """Response model for recommendation analysis."""
    wai_number: str = Field(..., description="WAI application number")
    recommendation_number: int = Field(..., description="Recommendation number (1 or 2)")
    summary: str = Field(..., description="Summary of recommendation quality")
    strengths: List[str] = Field(..., description="Recommendation strengths")
    concerns: List[str] = Field(..., description="Recommendation concerns")
    score: Optional[int] = Field(None, description="Recommendation score if available")
    processed_date: str = Field(..., description="When the analysis was processed")


class ErrorResponse(BaseModel):
    """Response model for errors."""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Additional error details")

# Made with Bob

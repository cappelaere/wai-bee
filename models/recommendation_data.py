"""Data models for recommendation analysis.

This module contains Pydantic models for validating and structuring
recommendation letter analysis data.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-05
Version: 1.0.0
License: MIT
"""

from datetime import datetime, timezone
from typing import Literal, Union, Optional
from pydantic import BaseModel, Field


class RecommendationItem(BaseModel):
    """Analysis of an individual recommendation letter.
    
    Attributes:
        recommender_role: Role/title of the person writing the recommendation.
        relationship_duration: How long the recommender has known the applicant.
        key_strengths_mentioned: List of key strengths highlighted.
        specific_examples: Concrete examples provided in the letter.
        potential_concerns: Any concerns or weaknesses mentioned.
        overall_tone: Overall sentiment of the recommendation.
    """
    recommender_role: str
    relationship_duration: str
    key_strengths_mentioned: list[str]
    specific_examples: list[str]
    potential_concerns: list[str]
    overall_tone: Literal["very_positive", "positive", "neutral", "mixed"]


class AggregateAnalysis(BaseModel):
    """Aggregate analysis across multiple recommendations.
    
    Attributes:
        common_themes: Themes that appear across multiple letters.
        strength_consistency: How consistent the strengths are across letters.
        depth_of_support: Overall depth and quality of support shown.
    """
    common_themes: list[str]
    strength_consistency: str
    depth_of_support: str


class ProfileFeatures(BaseModel):
    """Profile features extracted from recommendations.
    
    Attributes:
        recommendations: List of individual recommendation analyses.
        aggregate_analysis: Cross-recommendation aggregate analysis.
    """
    recommendations: list[RecommendationItem] = []
    aggregate_analysis: Optional[AggregateAnalysis] = None


class Scores(BaseModel):
    """Scoring metrics for recommendation quality.
    
    Attributes:
        average_support_strength_score: Average strength of support (0-100).
        consistency_of_support_score: Consistency across letters (0-100).
        depth_of_endorsement_score: Depth and specificity of endorsements (0-100).
        overall_score: Overall recommendation quality score (0-100).
    """
    average_support_strength_score: Union[int, float] = 0
    consistency_of_support_score: Union[int, float] = 0
    depth_of_endorsement_score: Union[int, float] = 0
    overall_score: Union[int, float] = 0


class ScoreBreakdown(BaseModel):
    """Reasoning behind the scores.
    
    Attributes:
        average_support_strength_score_reasoning: Explanation for support strength score.
        consistency_of_support_score_reasoning: Explanation for consistency score.
        depth_of_endorsement_score_reasoning: Explanation for depth score.
    """
    average_support_strength_score_reasoning: str = "Not provided"
    consistency_of_support_score_reasoning: str = "Not provided"
    depth_of_endorsement_score_reasoning: str = "Not provided"


class RecommendationData(BaseModel):
    """Complete recommendation analysis output.
    
    This is the main data model that matches the JSON schema for
    recommendation agent output.
    
    Attributes:
        wai_number: WAI application number.
        summary: Executive summary of the recommendations.
        profile_features: Detailed analysis of recommendation content.
        scores: Numerical scores for various metrics.
        score_breakdown: Reasoning behind the scores.
        processed_date: When the analysis was performed.
        source_files: List of recommendation files analyzed.
        model_used: LLM model used for analysis.
        criteria_used: Path to criteria file used.
    """
    wai_number: str
    summary: str
    profile_features: ProfileFeatures
    scores: Scores
    score_breakdown: ScoreBreakdown
    processed_date: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_files: list[str]
    model_used: str
    criteria_used: Optional[str] = None


class ProcessingError(BaseModel):
    """Error information for failed processing.
    
    Attributes:
        wai_number: WAI number where error occurred.
        error_type: Type of error (e.g., 'FileNotFound', 'ValidationError').
        error_message: Detailed error message.
        timestamp: When the error occurred.
    """
    wai_number: str
    error_type: str
    error_message: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ProcessingResult(BaseModel):
    """Statistics for a batch processing run.
    
    Attributes:
        total: Total number of WAI folders attempted.
        successful: Number successfully processed.
        failed: Number that failed.
        skipped: Number skipped (e.g., insufficient files).
        errors: List of errors encountered.
        duration: Total processing time in seconds.
        average_per_wai: Average processing time per WAI.
    """
    total: int
    successful: int
    failed: int
    skipped: int = 0
    errors: list[ProcessingError] = Field(default_factory=list)
    duration: float
    average_per_wai: float = 0.0

    def __init__(self, **data):
        super().__init__(**data)
        if self.total > 0:
            self.average_per_wai = self.duration / self.total


# Made with Bob
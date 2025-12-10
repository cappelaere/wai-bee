"""Data models for Essay Agent.

This module contains Pydantic models for personal essay analysis,
including motivation, goals, character traits, and scoring.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-06
Version: 1.0.0
License: MIT
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ProfileFeatures(BaseModel):
    """Personal profile features extracted from essays.
    
    Attributes:
        motivation_summary: Summary of applicant's motivation for aviation.
        career_goals_summary: Summary of career goals and aspirations.
        aviation_path_stage: Current stage in aviation journey.
        community_service_summary: Summary of community involvement.
        leadership_roles: List of leadership positions held.
        personal_character_indicators: List of character traits demonstrated.
        alignment_with_wai: How well applicant aligns with WAI values.
        unique_strengths: List of unique strengths or qualities.
    """
    motivation_summary: Optional[str] = None
    career_goals_summary: Optional[str] = None
    aviation_path_stage: Optional[str] = None
    community_service_summary: Optional[str] = None
    leadership_roles: list[Optional[str]] = Field(default_factory=list)
    personal_character_indicators: list[Optional[str]] = Field(default_factory=list)
    alignment_with_wai: Optional[str] = None
    unique_strengths: list[Optional[str]] = Field(default_factory=list)


class Scores(BaseModel):
    """Personal profile evaluation scores.
    
    All scores are on a 0-100 scale.
    
    Attributes:
        motivation_score: Score for passion and commitment to aviation.
        goals_clarity_score: Score for clarity and realism of career goals.
        character_service_leadership_score: Score for character, service, and leadership.
        overall_score: Overall personal profile score.
    """
    motivation_score: Optional[int] = 0
    goals_clarity_score: Optional[int] = 0
    character_service_leadership_score: Optional[int] = 0
    overall_score: Optional[int] = 0


class ScoreBreakdown(BaseModel):
    """Detailed reasoning for each score.
    
    Attributes:
        motivation_score_reasoning: Explanation for motivation score.
        goals_clarity_score_reasoning: Explanation for goals clarity score.
        character_service_leadership_score_reasoning: Explanation for character/service/leadership score.
        overall_score_reasoning: Explanation for overall score.
    """
    motivation_score_reasoning: str = "Not provided"
    goals_clarity_score_reasoning: str = "Not provided"
    character_service_leadership_score_reasoning: str = "Not provided"
    overall_score_reasoning: str = "Not provided"


class EssayData(BaseModel):
    """Complete personal essay analysis data.
    
    Attributes:
        wai_number: WAI application number.
        summary: Executive summary of personal profile.
        profile_features: Detailed personal profile features.
        scores: Numerical scores for personal evaluation.
        score_breakdown: Detailed reasoning for scores.
        processed_date: ISO 8601 timestamp of processing.
        source_files: List of source essay file names.
        model_used: LLM model used for analysis.
        criteria_used: Path to criteria file used.
    """
    wai_number: str
    summary: str = "Unknown"
    profile_features: ProfileFeatures = Field(default_factory=ProfileFeatures)
    scores: Scores = Field(default_factory=Scores)
    score_breakdown: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    processed_date: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    source_files: list[str] = Field(default_factory=list)
    model_used: str
    criteria_used: str


class ProcessingResult(BaseModel):
    """Result of batch essay processing.
    
    Attributes:
        total: Total number of WAI folders processed.
        successful: Number successfully processed.
        failed: Number that failed processing.
        skipped: Number skipped (no essays or already processed).
        errors: List of processing errors.
        duration: Total processing time in seconds.
    """
    total: int
    successful: int
    failed: int
    skipped: int
    errors: list['ProcessingError'] = Field(default_factory=list)
    duration: float
    
    @property
    def average_per_wai(self) -> float:
        """Calculate average processing time per WAI."""
        if self.successful == 0:
            return 0.0
        return self.duration / self.successful


class ProcessingError(BaseModel):
    """Error information for failed processing.
    
    Attributes:
        wai_number: WAI application number that failed.
        error_type: Type of error encountered.
        error_message: Detailed error message.
    """
    wai_number: str
    error_type: str
    error_message: str

# Made with Bob

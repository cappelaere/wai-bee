"""Data models for Academic Agent.

This module contains Pydantic models for academic profile analysis,
including education details, academic performance, and scoring.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-05
Version: 1.0.0
License: MIT
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ProfileFeatures(BaseModel):
    """Academic profile features extracted from resume/CV.
    
    Attributes:
        current_school_name: Name of current educational institution.
        program: Academic program or major.
        education_level: Level of education (Bachelor's, Master's, etc.).
        gpa: Grade point average.
        academic_awards: List of academic honors and awards.
        relevant_courses: List of relevant coursework.
        academic_trajectory: Description of academic progress and trends.
        strengths: List of academic strengths.
        areas_for_improvement: List of areas needing development.
    """
    current_school_name: Optional[str] = None
    program: Optional[str] = None
    education_level: Optional[str] = None
    gpa: Optional[str] = None
    academic_awards: list[Optional[str]] = Field(default_factory=list)
    relevant_courses: list[Optional[str]] = Field(default_factory=list)
    academic_trajectory: Optional[str] = None
    strengths: list[Optional[str]] = Field(default_factory=list)
    areas_for_improvement: list[Optional[str]] = Field(default_factory=list)


class Scores(BaseModel):
    """Academic evaluation scores.
    
    All scores are on a 0-100 scale.
    
    Attributes:
        academic_performance_score: Score for GPA, grades, and academic achievement.
        academic_relevance_score: Score for program relevance to aviation/scholarship.
        academic_readiness_score: Score for preparedness for aviation training.
        overall_score: Overall academic profile score.
    """
    academic_performance_score: int = 0
    academic_relevance_score: int = 0
    academic_readiness_score: int = 0
    overall_score: int = 0


class ScoreBreakdown(BaseModel):
    """Detailed reasoning for each score.
    
    Attributes:
        academic_performance_score_reasoning: Explanation for performance score.
        academic_relevance_score_reasoning: Explanation for relevance score.
        academic_readiness_score_reasoning: Explanation for readiness score.
    """
    academic_performance_score_reasoning: str = "Not provided"
    academic_relevance_score_reasoning: str = "Not provided"
    academic_readiness_score_reasoning: str = "Not provided"


class AcademicData(BaseModel):
    """Complete academic profile analysis data.
    
    Attributes:
        wai_number: WAI application number.
        summary: Executive summary of academic profile.
        profile_features: Detailed academic profile features.
        scores: Numerical scores for academic evaluation.
        score_breakdown: Detailed reasoning for scores.
        processed_date: ISO 8601 timestamp of processing.
        source_file: Name of source resume file.
        model_used: LLM model used for analysis.
        criteria_used: Path to criteria file used.
    """
    wai_number: str
    summary: str = "Unknown"
    profile_features: ProfileFeatures = Field(default_factory=ProfileFeatures)
    scores: Scores = Field(default_factory=Scores)
    score_breakdown: ScoreBreakdown = Field(default_factory=ScoreBreakdown)
    processed_date: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    source_file: str
    model_used: str
    criteria_used: str


class ProcessingResult(BaseModel):
    """Result of batch academic profile processing.
    
    Attributes:
        total: Total number of WAI folders processed.
        successful: Number successfully processed.
        failed: Number that failed processing.
        skipped: Number skipped (no resume or already processed).
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

"""Analysis endpoints for applications, academics, essays, and recommendations.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-16
Version: 1.0.0
License: MIT
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from fastapi_cache.decorator import cache
from typing import Any, Dict
from ..api_utils import get_data_service

router = APIRouter(tags=["Analysis"])
logger = logging.getLogger(__name__)


@router.get("/application", operation_id="get_application")
@cache(expire=3600)  # Cache for 60 minutes
async def get_application_analysis(
    scholarship: str = Query(..., description="Scholarship name (e.g., 'Delaney_Wings' or 'Evans_Wings')"),
    wai_number: str = Query(..., description="WAI application number")
):
    """Get detailed application analysis.
    
    Args:
        scholarship: Name of the scholarship
        wai_number: WAI application number
        
    Returns:
        ApplicationAnalysisResponse with detailed analysis
    """
    data_service = get_data_service(scholarship)
    
    try:
        analysis = data_service.load_application_analysis(wai_number)
        if not analysis:
            raise HTTPException(status_code=404, detail=f"Application {wai_number} not found")
        
        return analysis
    
    except Exception as e:
        logger.exception("Error getting application analysis for %s", wai_number)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resume", operation_id="get_resume")
async def get_resume_analysis(
    scholarship: str = Query(..., description="Scholarship name (e.g., 'Delaney_Wings' or 'Evans_Wings')"),
    wai_number: str = Query(..., description="WAI application number")
):
    """Get resume analysis for an application.
    
    Args:
        scholarship: Name of the scholarship
        wai_number: WAI application number
        
    Returns:
        ResumeAnalysisResponse with resume analysis
    """
    data_service = get_data_service(scholarship)
    
    try:
        analysis = data_service.load_resume_analysis(wai_number)
        if not analysis:
            raise HTTPException(
                status_code=404,
                detail=f"Resume analysis for {wai_number} not found"
            )
        
        return analysis
  
    except Exception as e:
        logger.exception("Error getting resume analysis for %s", wai_number)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/essay", operation_id="list_essays")
async def get_essay_analysis(
    scholarship: str = Query(..., description="Scholarship name (e.g., 'Delaney_Wings' or 'Evans_Wings')"),
    wai_number: str = Query(..., description="WAI application number")
):
    """Get combined essay analysis for an application.
    
    Args:
        scholarship: Name of the scholarship
        wai_number: WAI application number
        
    Returns:
        Combined analysis of all essays
    """
    data_service = get_data_service(scholarship)
    
    try:
        combined = data_service.load_combined_essay_analysis(wai_number)
        if not combined:
            raise HTTPException(
                status_code=404,
                detail=f"No essay analyses found for {wai_number}"
            )
        
        return combined
   
    except Exception as e:
        logger.exception("Error getting essay analysis for %s", wai_number)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/essay", operation_id="get_essay")
async def get_single_essay_analysis(
    essay_number: int = Query(..., description="Essay number (1 or 2)", example=1),
    scholarship: str = Query(..., description="Scholarship name (e.g., 'Delaney_Wings' or 'Evans_Wings')"),
    wai_number: str = Query(..., description="WAI application number")
):
    """Get analysis for a specific essay.
    
    Args:
        essay_number: Essay number (1 or 2)
        scholarship: Name of the scholarship
        wai_number: WAI application number
        
    Returns:
        EssayAnalysisResponse for the specified essay
    """
    if essay_number not in [1, 2]:
        raise HTTPException(status_code=400, detail="Essay number must be 1 or 2")
    
    data_service = get_data_service(scholarship)
    
    try:
        analysis = data_service.load_essay_analysis(wai_number, essay_number)
        if not analysis:
            raise HTTPException(
                status_code=404,
                detail=f"Essay {essay_number} analysis for {wai_number} not found"
            )
        
        return analysis
    
    except Exception as e:
        logger.exception("Error getting essay %d analysis for %s", essay_number, wai_number)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendation", operation_id="list_recs")
async def get_recommendation_analysis(
    scholarship: str = Query(..., description="Scholarship name (e.g., 'Delaney_Wings' or 'Evans_Wings')"),
    wai_number: str = Query(..., description="WAI application number")
):
    """Get combined recommendation analysis for an application.
    
    Args:
        scholarship: Name of the scholarship
        wai_number: WAI application number
        
    Returns:
        Combined analysis of all recommendations
    """
    data_service = get_data_service(scholarship)
    
    try:
        combined = data_service.load_combined_recommendation_analysis(wai_number)
        if not combined:
            raise HTTPException(
                status_code=404,
                detail=f"No recommendation analyses found for {wai_number}"
            )
        
        return combined
    
    except Exception as e:
        logger.exception("Error getting recommendation analysis for %s", wai_number)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/recommendation/by-number", operation_id="get_recommendation")
async def get_single_recommendation_analysis(
    rec_number: int = Query(..., description="Recommendation number (1 or 2)", example=1),
    scholarship: str = Query(..., description="Scholarship name (e.g., 'Delaney_Wings' or 'Evans_Wings')"),
    wai_number: str = Query(..., description="WAI application number")
):
    """Get analysis for a specific recommendation.
    
    Args:
        rec_number: Recommendation number (1 or 2)
        scholarship: Name of the scholarship
        wai_number: WAI application number
        
    Returns:
        RecommendationAnalysisResponse for the specified recommendation
    """
    if rec_number not in [1, 2]:
        raise HTTPException(status_code=400, detail="Recommendation number must be 1 or 2")
    
    data_service = get_data_service(scholarship)
    
    try:
        analysis = data_service.load_recommendation_analysis(wai_number, rec_number)
        if not analysis:
            raise HTTPException(
                status_code=404,
                detail=f"Recommendation {rec_number} analysis for {wai_number} not found"
            )
        
        return analysis
  
    except Exception as e:
        logger.exception("Error getting recommendation %d analysis for %s", rec_number, wai_number)
        raise HTTPException(status_code=500, detail=str(e))

# Made with Bob

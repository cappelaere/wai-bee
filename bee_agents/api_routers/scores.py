"""Score and statistics endpoints.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-16
Version: 1.0.0
License: MIT
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from ..models import ScoreResponse, TopScoresResponse, StatisticsResponse
from ..api_utils import get_data_service

router = APIRouter(tags=["Scores"])
logger = logging.getLogger(__name__)


@router.get("/score", response_model=ScoreResponse, operation_id="get_score")
async def get_score(
    scholarship: str = Query(..., description="Scholarship name (e.g., 'Delaney_Wings' or 'Evans_Wings')"),
    wai_number: str = Query(..., description="WAI application number")
):
    """Get score for a specific application.
    
    Args:
        scholarship: Name of the scholarship
        wai_number: WAI application number
        
    Returns:
        ScoreResponse with application scores
    """
    data_service = get_data_service(scholarship)
    
    try:
        # Get all scores and find the one matching the WAI number
        all_scores = data_service.get_all_scores()
        score = next((s for s in all_scores if s.get("wai_number") == wai_number), None)
        
        if not score:
            raise HTTPException(
                status_code=404,
                detail=f"Score for application {wai_number} not found"
            )
        
        return ScoreResponse(**score)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting score for {wai_number}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top_scores", response_model=TopScoresResponse, operation_id="get_top_scores")
async def get_top_scores(
    scholarship: str = Query(..., description="Scholarship name (e.g., 'Delaney_Wings' or 'Evans_Wings')"),
    limit: int = Query(10, ge=1, le=100, description="Number of top scores to return")
):
    """Get top scoring applications.
    
    Args:
        scholarship: Name of the scholarship
        limit: Number of top scores to return (1-100)
        
    Returns:
        TopScoresResponse with list of top scoring applications
    """
    data_service = get_data_service(scholarship)
    
    try:
        top_scores = data_service.get_top_scores(limit)
        all_scores = data_service.get_all_scores()
        total_applications = len(all_scores)
        
        return TopScoresResponse(
            scholarship=scholarship,
            total_applications=total_applications,
            top_scores=top_scores
        )
    except Exception as e:
        logger.error(f"Error getting top scores for {scholarship}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics", response_model=StatisticsResponse, operation_id="get_statistics")
async def get_statistics(
    scholarship: str = Query(..., description="Scholarship name (e.g., 'Delaney_Wings' or 'Evans_Wings')")
):
    """Get aggregated statistics for all applications.
    
    Args:
        scholarship: Name of the scholarship
        
    Returns:
        StatisticsResponse with aggregated statistics
    """
    data_service = get_data_service(scholarship)
    
    try:
        stats = data_service.get_statistics()
        if not stats:
            raise HTTPException(
                status_code=404,
                detail=f"No statistics available for {scholarship}"
            )
        
        # Add scholarship field to stats
        stats["scholarship"] = scholarship
        return StatisticsResponse(**stats)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting statistics for {scholarship}: {e}",
            extra={
                "scholarship": scholarship,
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        raise HTTPException(status_code=500, detail=str(e))

# Made with Bob

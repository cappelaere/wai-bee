"""Criteria management endpoints.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-16
Version: 1.0.0
License: MIT
"""

import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse
from ..api_utils import get_data_service

router = APIRouter(tags=["Criteria"])
logger = logging.getLogger(__name__)


@router.get("/criteria", operation_id="list_criteria")
async def list_criteria(
    request: Request,
    scholarship: str = Query(..., description="Scholarship name (e.g., 'Delaney_Wings' or 'Evans_Wings')")
):
    """List all available criteria files for a scholarship with fully qualified URLs.
    
    Args:
        scholarship: Name of the scholarship
        
    Returns:
        Dictionary with list of criteria and their download URLs
    """
    get_data_service(scholarship)  # Validate scholarship exists
    
    criteria_dir = Path("data") / scholarship / "criteria"
    
    if not criteria_dir.exists():
        logger.warning(f"Criteria directory not found: {criteria_dir}")
        raise HTTPException(
            status_code=404,
            detail=f"No criteria found for scholarship: {scholarship}"
        )
    
    # Get base URL from request
    base_url = str(request.base_url).rstrip('/') if request else "http://localhost:8200"
    
    criteria_files = []
    for file_path in sorted(criteria_dir.glob("*.txt")):
        criteria_name = file_path.stem  # filename without extension
        criteria_files.append({
            "name": criteria_name,
            "filename": file_path.name,
            "url": f"{base_url}/criteria/{scholarship}/{file_path.name}"
        })
    
    logger.info(f"Listed {len(criteria_files)} criteria files for {scholarship}")
    
    return {
        "scholarship": scholarship,
        "criteria_count": len(criteria_files),
        "criteria": criteria_files
    }


@router.get("/criteria/{scholarship}/{filename}", operation_id="get_criteria_file")
async def get_criteria_file(
    scholarship: str,
    filename: str
):
    """Download a specific criteria file.
    
    Args:
        scholarship: Name of the scholarship
        filename: Name of the criteria file
        
    Returns:
        File content as plain text
    """
    get_data_service(scholarship)  # Validate scholarship exists
    
    # Validate filename (security: prevent path traversal)
    if not filename.endswith('.txt') or '/' in filename or '\\' in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    criteria_path = Path("data") / scholarship / "criteria" / filename
    
    if not criteria_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Criteria file not found: {filename}"
        )
    
    logger.info(f"Serving criteria file: {scholarship}/{filename}")
    
    return FileResponse(
        path=criteria_path,
        media_type="text/plain",
        filename=filename
    )

# Made with Bob

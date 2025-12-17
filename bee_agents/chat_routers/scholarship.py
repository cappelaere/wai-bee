"""Scholarship selection endpoints.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-16
Version: 1.0.0
License: MIT
"""

import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Cookie, Request, Body
from fastapi.responses import HTMLResponse
from fastapi_cache.decorator import cache
from ..auth import verify_token_with_context, active_tokens
from ..middleware import ScholarshipAccessMiddleware

router = APIRouter(tags=["Scholarship"])
logger = logging.getLogger(__name__)


@router.get("/select-scholarship", response_class=HTMLResponse, operation_id="get_select_page")
async def get_scholarship_selection_page(request: Request):
    """Serve the scholarship selection page.
    
    Note: HTML responses are not cached as they are static files.
    """
    template_path = Path(__file__).parent.parent / "templates" / "select_scholarship.html"
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        logger.error(f"Scholarship selection template not found: {template_path}")
        raise HTTPException(status_code=500, detail="Template not found")


@router.post("/api/user/select-scholarship", operation_id="select_scholarship")
async def select_scholarship(
    request: Request,
    payload: dict = Body(...),
    auth_token: Optional[str] = Cookie(None)
):
    """Store the user's selected scholarship in their session."""
    if not auth_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token_data = verify_token_with_context(auth_token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    scholarship = payload.get("scholarship")
    if not scholarship:
        raise HTTPException(status_code=400, detail="Scholarship not provided")
    
    # Verify user has access to this scholarship
    middleware = ScholarshipAccessMiddleware(token_data)
    if not middleware.can_access_scholarship(scholarship):
        raise HTTPException(status_code=403, detail="Access denied to this scholarship")
    
    # Store selected scholarship in token data
    if auth_token in active_tokens:
        active_tokens[auth_token]["selected_scholarship"] = scholarship
        logger.info(
            f"User selected scholarship: {token_data['username']} -> {scholarship}",
            extra={
                "username": token_data["username"],
                "scholarship": scholarship
            }
        )
    
    return {"message": "Scholarship selected successfully", "scholarship": scholarship}


@router.get("/api/user/scholarships", operation_id="get_scholarships")
async def get_user_scholarships(
    request: Request,
    auth_token: Optional[str] = Cookie(None)
):
    """Get list of scholarships accessible to the current user."""
    if not auth_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token_data = verify_token_with_context(auth_token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    try:
        middleware = ScholarshipAccessMiddleware(token_data)
        scholarships = middleware.get_accessible_scholarships()
        
        # Return just the scholarships array for frontend compatibility
        return scholarships
    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e}")
        raise HTTPException(
            status_code=500,
            detail="Scholarship configuration not found. Please contact administrator."
        )
    except ValueError as e:
        logger.error(f"Invalid configuration: {e}")
        raise HTTPException(
            status_code=500,
            detail="Invalid scholarship configuration. Please contact administrator."
        )
    except Exception as e:
        logger.error(f"Error loading scholarships: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to load scholarships. Please try again or contact administrator."
        )

# Made with Bob

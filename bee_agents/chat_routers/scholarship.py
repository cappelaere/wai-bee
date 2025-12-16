"""Scholarship selection endpoints.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-16
Version: 1.0.0
License: MIT
"""

import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Cookie
from fastapi.responses import HTMLResponse
from ..auth import verify_token_with_context, active_tokens
from ..middleware import ScholarshipAccessMiddleware

router = APIRouter(tags=["Scholarship"])
logger = logging.getLogger(__name__)


@router.get("/select-scholarship", response_class=HTMLResponse, operation_id="get_select_page")
async def get_scholarship_selection_page():
    """Serve the scholarship selection page."""
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
    request: dict,
    auth_token: Optional[str] = Cookie(None)
):
    """Store the user's selected scholarship in their session."""
    if not auth_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token_data = verify_token_with_context(auth_token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    scholarship = request.get("scholarship")
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
async def get_user_scholarships(auth_token: Optional[str] = Cookie(None)):
    """Get list of scholarships accessible to the current user."""
    if not auth_token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    token_data = verify_token_with_context(auth_token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    middleware = ScholarshipAccessMiddleware(token_data)
    scholarships = middleware.get_accessible_scholarships()
    
    return {
        "username": token_data["username"],
        "role": token_data["role"],
        "scholarships": scholarships
    }

# Made with Bob

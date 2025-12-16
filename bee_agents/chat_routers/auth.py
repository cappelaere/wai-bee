"""Authentication endpoints for chat interface.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-16
Version: 1.0.0
License: MIT
"""

import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse
from ..auth import (
    LoginRequest,
    LoginResponse,
    create_token_with_context,
    verify_credentials,
    revoke_token
)

router = APIRouter(tags=["Authentication"])
logger = logging.getLogger(__name__)


@router.get("/login", response_class=HTMLResponse, operation_id="get_login_page")
async def get_login_page():
    """Serve the login page."""
    template_path = Path(__file__).parent.parent / "templates" / "login.html"
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        logger.error(f"Login template not found: {template_path}")
        raise HTTPException(status_code=500, detail="Login template not found")


@router.post("/login", response_model=LoginResponse, operation_id="login")
async def login(request: LoginRequest):
    """Handle login requests with scholarship context."""
    if not verify_credentials(request.username, request.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    token_response = create_token_with_context(request.username)
    logger.info(
        f"User logged in: {request.username}",
        extra={
            "username": request.username,
            "role": token_response["role"],
            "scholarships": token_response["scholarships"]
        }
    )
    
    return LoginResponse(**token_response)


@router.post("/logout", operation_id="logout")
async def logout(token: str):
    """Handle logout requests."""
    success = revoke_token(token)
    if success:
        return {"message": "Logged out successfully"}
    return {"message": "Token not found or already expired"}

# Made with Bob

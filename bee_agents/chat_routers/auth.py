"""Authentication endpoints for chat interface.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-16
Version: 1.0.0
License: MIT
"""

import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from ..auth import (
    LoginRequest,
    LoginResponse,
    create_token_with_context,
    verify_credentials,
    revoke_token
)

router = APIRouter(tags=["Authentication"])
logger = logging.getLogger(__name__)

# Rate limiter for auth endpoints
limiter = Limiter(key_func=get_remote_address)


@router.get("/login", response_class=HTMLResponse, operation_id="get_login_page")
@limiter.limit("60/minute")
async def get_login_page(request: Request):
    """Serve the login page.
    
    Rate limit: 60 requests per minute per IP address.
    """
    template_path = Path(__file__).parent.parent / "templates" / "login.html"
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        logger.error(f"Login template not found: {template_path}")
        raise HTTPException(status_code=500, detail="Login template not found")


@router.post("/login", response_model=LoginResponse, operation_id="login")
@limiter.limit("10/minute")
async def login(request: Request, credentials: LoginRequest):
    """Handle login requests with scholarship context.
    
    Rate limit: 10 login attempts per minute per IP address to prevent brute force attacks.
    """
    if not verify_credentials(credentials.username, credentials.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    token_response = create_token_with_context(credentials.username)
    logger.info(
        f"User logged in: {credentials.username}",
        extra={
            "username": credentials.username,
            "role": token_response["role"],
            "scholarships": token_response["scholarships"]
        }
    )
    
    return LoginResponse(**token_response)


@router.post("/logout", operation_id="logout")
@limiter.limit("30/minute")
async def logout(request: Request, token: str):
    """Handle logout requests.
    
    Rate limit: 30 requests per minute per IP address.
    """
    success = revoke_token(token)
    if success:
        return {"message": "Logged out successfully"}
    return {"message": "Token not found or already expired"}

# Made with Bob

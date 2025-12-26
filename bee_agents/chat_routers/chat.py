"""WebSocket chat endpoint and related functionality.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-16
Version: 1.0.0
License: MIT
"""

import logging
from pathlib import Path
from typing import Optional, Dict
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Cookie, Request
from fastapi.responses import HTMLResponse, FileResponse, Response
from slowapi import Limiter
from slowapi.util import get_remote_address

router = APIRouter(tags=["Chat"])
logger = logging.getLogger(__name__)

# Rate limiter for chat endpoints
limiter = Limiter(key_func=get_remote_address)

# Simple in-memory cache for HTML templates to avoid repeatedly opening files
_template_cache: Dict[str, str] = {}


def _load_template(template_name: str, fallback: str) -> str:
    """Load an HTML template from disk with simple caching.
    
    This avoids repeatedly opening the same file on every request,
    which can contribute to 'Too many open files' errors under load.
    """
    if template_name in _template_cache:
        return _template_cache[template_name]

    template_path = Path(__file__).parent.parent / "templates" / template_name

    try:
        html_content = template_path.read_text(encoding="utf-8")
        _template_cache[template_name] = html_content
        return html_content
    except FileNotFoundError:
        logger.error(f"Template not found: {template_path}")
        return fallback


@router.get("/", response_class=HTMLResponse, operation_id="get_chat_page")
@limiter.limit("60/minute")
async def get_chat_page(request: Request):
    """Serve the main chat interface.
    
    Rate limit: 60 requests per minute per IP address.
    """
    html_content = _load_template(
        "chat.html",
        "<h1>Chat interface not found</h1>",
    )
    status = 200 if html_content.strip().startswith("<!DOCTYPE") or "not found" not in html_content else 500
    return HTMLResponse(content=html_content, status_code=status)


@router.get("/about", response_class=HTMLResponse, operation_id="get_about_page")
@limiter.limit("60/minute")
async def get_about_page(request: Request):
    """Serve the about page.
    
    Rate limit: 60 requests per minute per IP address.
    """
    html_content = _load_template(
        "about.html",
        "<h1>About page not found</h1>",
    )
    status = 200 if html_content.strip().startswith("<!DOCTYPE") or "not found" not in html_content else 500
    return HTMLResponse(content=html_content, status_code=status)


@router.get("/examples", response_class=HTMLResponse, operation_id="get_examples_page")
async def get_examples_page(request: Request):
    """Serve the examples page."""
    html_content = _load_template(
        "examples.html",
        "<h1>Examples page not found</h1>",
    )
    status = 200 if html_content.strip().startswith("<!DOCTYPE") or "not found" not in html_content else 500
    return HTMLResponse(content=html_content, status_code=status)


@router.get("/health", operation_id="chat_health_check")
async def health_check(request: Request):
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "chat-frontend"
    }


@router.get("/favicon.ico", operation_id="get_favicon")
async def favicon(request: Request):
    """Serve the favicon."""
    favicon_path = Path(__file__).parent.parent / "static" / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(favicon_path, media_type="image/x-icon")
    return Response(status_code=204)


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat communication.
    
    This endpoint handles bidirectional communication between the client
    and the agent handler (either multi-agent or single-agent mode).
    """
    await websocket.accept()
    logger.info("WebSocket connection established")
    
    try:
        # Get agent handler from app state
        # This is set during app initialization in chat_api.py
        agent_handler = websocket.app.state.agent_handler
        
        if not agent_handler:
            await websocket.send_json({
                "error": "Agent handler not initialized",
                "type": "system_error"
            })
            await websocket.close()
            return
        
        # Main message loop
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            logger.debug(f"Received message: {data.get('type', 'unknown')}")
            
            # Process message with agent handler
            # The agent handler will stream responses back through the websocket
            try:
                # Import here to avoid circular dependencies
                from ..chat_agents import MultiAgentOrchestrator
                from ..chat_agents_single import SingleAgentHandler
                
                if isinstance(agent_handler, MultiAgentOrchestrator):
                    await agent_handler.process_message(websocket, data)
                elif isinstance(agent_handler, SingleAgentHandler):
                    await agent_handler.process_message(websocket, data)
                else:
                    await websocket.send_json({
                        "error": "Unknown agent handler type",
                        "type": "system_error"
                    })
            
            except Exception as e:
                logger.error(f"Error processing message: {e}", exc_info=True)
                await websocket.send_json({
                    "error": str(e),
                    "type": "processing_error"
                })
    
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected normally")
    
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
        try:
            await websocket.close()
        except:
            pass


@router.get("/admin/config", response_class=HTMLResponse, operation_id="get_admin_config")
async def get_admin_config_page():
    """Serve the admin configuration page."""
    html_content = _load_template(
        "admin_config.html",
        "<h1>Admin configuration page not found</h1>",
    )
    status = 200 if html_content.strip().startswith("<!DOCTYPE") or "not found" not in html_content else 500
    return HTMLResponse(content=html_content, status_code=status)

# Made with Bob

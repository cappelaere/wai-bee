"""FastAPI chat interface for the scholarship agent.

This module provides a web-based chat interface for interacting with
the scholarship agent using WebSockets for real-time communication.

Supports both multi-agent orchestration and single-agent modes.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-08
Version: 2.0.0
License: MIT

Example:
    Run the chat server with multi-agent mode (default)::
    
        python bee_agents/chat_api.py --port 8100
    
    Run with single-agent mode::
    
        AGENT_MODE=single python bee_agents/chat_api.py --port 8100
"""

import asyncio
import os, json
import logging
import time
from pathlib import Path
from typing import Optional, Union, Dict, Any
from contextlib import asynccontextmanager
import argparse

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Cookie, Depends
from fastapi.responses import HTMLResponse, FileResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles


# Setup Bee internal logging
# from beeai_framework.logger import Logger
# beeLogger = Logger('bee_chat_api', level='INFO')

from .auth import (
    LoginRequest,
    LoginResponse,
    create_token,
    create_token_with_context,
    verify_token,
    verify_token_with_context,
    verify_credentials,
    revoke_token
)
from .middleware import ScholarshipAccessMiddleware, log_access_attempt
from .logging_config import setup_logging
from .chat_agents import MultiAgentOrchestrator
from .chat_agents_single import SingleAgentHandler

# OpenInference BeeAI instrumentation with OpenTelemetry
from openinference.instrumentation.beeai import BeeAIInstrumentor
from opentelemetry import trace as trace_api
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk import trace as trace_sdk
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import SimpleSpanProcessor


# Configure logging
logger = setup_logging('chat')

# Global agent handler (either multi-agent or single-agent)
agent_handler: Optional[Union[MultiAgentOrchestrator, SingleAgentHandler]] = None

# Agent mode configuration
AGENT_MODE = os.environ.get("AGENT_MODE", "single").lower()  # "multi" or "single"

# Model configuration - supports any provider (Anthropic, Ollama, OpenAI, etc.)
# Format: "provider:model-name" or just "model-name" for default provider
CHAT_MODEL = os.environ.get("CHAT_MODEL", "anthropic:claude-sonnet-4-20250514")
ORCHESTRATOR_MODEL = os.environ.get("ORCHESTRATOR_MODEL", CHAT_MODEL)  # Can use different model for routing (multi-agent only)

logger.info(f"Agent mode: {AGENT_MODE}")
logger.info(f"Chat model configuration: {CHAT_MODEL}")
if AGENT_MODE == "multi":
    logger.info(f"Orchestrator model configuration: {ORCHESTRATOR_MODEL}")

def setup_observability() -> None:
    """Setup observability using OpenInference BeeAI instrumentation with OTLP."""
    
    LANGFUSE_ENABLED = os.environ.get("LANGFUSE_ENABLED", "false").lower() == "true"
    if LANGFUSE_ENABLED:
        try:
            # Get Langfuse configuration
            langfuse_host = os.environ.get("LANGFUSE_HOST", "http://langfuse:3000")
            public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "")
            secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "")
            
            if not public_key or not secret_key:
                logger.warning("Langfuse keys not configured, skipping observability setup")
                return
            
            # Construct OTLP endpoint - Langfuse v2 uses /api/public/otel/v1/traces
            otlp_endpoint = f"{langfuse_host}/api/public/otel/v1/traces"
            
            # Create Basic auth header
            import base64
            auth_string = base64.b64encode(f"{public_key}:{secret_key}".encode()).decode()
            headers = {"Authorization": f"Basic {auth_string}"}
            
            # Configure OpenTelemetry with OTLP exporter
            resource = Resource(attributes={})
            tracer_provider = trace_sdk.TracerProvider(resource=resource)
            
            # Create OTLP exporter with explicit endpoint and headers
            otlp_exporter = OTLPSpanExporter(
                endpoint=otlp_endpoint,
                headers=headers
            )
            
            tracer_provider.add_span_processor(SimpleSpanProcessor(otlp_exporter))
            trace_api.set_tracer_provider(tracer_provider)

            # Instrument BeeAI framework
            BeeAIInstrumentor().instrument()
            
            logger.info(f"OpenInference BeeAI instrumentation enabled - traces will be sent to {otlp_endpoint}")
            logger.info("OpenTelemetry OTLP integration initialized")
            
        except Exception as e:
            logger.error(f"Failed to setup observability: {e}", exc_info=True)
            logger.warning("Continuing without observability - chat functionality will work normally")
    else:
        logger.info("OpenInference observability is disabled")

async def initialize_agents():
    """Initialize agents based on configured mode (multi-agent or single-agent).
    
    Supports multiple model providers:
    - Anthropic: anthropic:claude-sonnet-4-20250514
    - Ollama: ollama/llama3.2:3b, ollama/qwen2.5:7b
    - OpenAI: openai:gpt-4, openai:gpt-3.5-turbo
    
    Agent modes:
    - multi: Multi-agent orchestration with specialized agents (default)
    - single: Single unified agent handling all tasks
    """
    global agent_handler
    
    logger.info(f"Initializing agent system in {AGENT_MODE} mode...")
    
    if AGENT_MODE == "single":
        # Single-agent mode
        agent_handler = SingleAgentHandler(CHAT_MODEL)
        await agent_handler.initialize()
        logger.info("Single-agent system initialized")
    else:
        # Multi-agent mode (default)
        agent_handler = MultiAgentOrchestrator(CHAT_MODEL, ORCHESTRATOR_MODEL)
        await agent_handler.initialize()
        logger.info("Multi-agent system initialized")
    
    logger.info("OpenInference observability is active")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    # Initialize observability BEFORE any BeeAI code runs
    setup_observability()
    await initialize_agents()
    yield
    # Shutdown (if needed in the future)


# Create FastAPI app
app = FastAPI(
    title="Scholarship Agent Chat",
    description="Interactive chat interface for scholarship analysis with multi-agent orchestration",
    version="2.0.0",
    lifespan=lifespan
)


# Mount static files directory
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/favicon.ico")
async def favicon():
    """Serve the favicon."""
    import os
    favicon_path = os.path.join(os.path.dirname(__file__), "static", "favicon.ico")
    if os.path.exists(favicon_path):
        return FileResponse(favicon_path, media_type="image/x-icon")
    from fastapi.responses import Response
    return Response(status_code=204)


@app.get("/login", response_class=HTMLResponse)
async def get_login_page():
    """Serve the login page."""
    template_path = Path(__file__).parent / "templates" / "login.html"
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        logger.error(f"Login template not found: {template_path}")
        raise HTTPException(status_code=500, detail="Login template not found")


@app.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Handle login requests with scholarship context."""
    # Verify credentials
    if not verify_credentials(request.username, request.password):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    # Create token with full context
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


@app.get("/select-scholarship", response_class=HTMLResponse)
async def get_scholarship_selection_page():
    """Serve the scholarship selection page."""
    template_path = Path(__file__).parent / "templates" / "select_scholarship.html"
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        logger.error(f"Scholarship selection template not found: {template_path}")
        raise HTTPException(status_code=500, detail="Template not found")


@app.post("/api/user/select-scholarship")
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
    from .auth import active_tokens
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


@app.post("/logout")
async def logout(auth_token: Optional[str] = Cookie(None)):
    """Handle logout requests."""
    if auth_token:
        username = verify_token(auth_token)
        if username:
            revoke_token(auth_token)
            logger.info(f"User logged out: {username}")
    
    return {"message": "Logged out successfully"}


@app.get("/about", response_class=HTMLResponse)
async def get_about_page():
    """Serve the about page (no authentication required)."""
    template_path = Path(__file__).parent / "templates" / "about.html"
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        logger.error(f"About template not found: {template_path}")
        raise HTTPException(status_code=500, detail="About template not found")


@app.get("/examples", response_class=HTMLResponse)
async def get_examples_page():
    """Serve the examples page (no authentication required)."""
    template_path = Path(__file__).parent / "templates" / "examples.html"
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        logger.error(f"Examples template not found: {template_path}")
        raise HTTPException(status_code=500, detail="Examples template not found")


@app.get("/admin/config", response_class=HTMLResponse)
async def get_admin_config_page(auth_token: Optional[str] = Cookie(None)):
    """Serve the admin configuration page (admin only)."""
    # Require authentication with context to check role
    token_data = verify_token_with_context(auth_token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Unauthorized")

    if token_data.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    template_path = Path(__file__).parent / "templates" / "admin_config.html"
    try:
        with open(template_path, "r", encoding="utf-8") as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        logger.error(f"Admin config template not found: {template_path}")
        raise HTTPException(status_code=500, detail="Admin config template not found")


def get_scholarship_config_path(scholarship_name: str) -> Path:
    """Get path to canonical config.yml for a scholarship."""
    return Path("data") / scholarship_name / "config.yml"


def load_scholarship_config(scholarship_name: str) -> Dict[str, Any]:
    """Load canonical scholarship config."""
    import yaml

    config_path = get_scholarship_config_path(scholarship_name)
    if not config_path.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Config file not found for scholarship {scholarship_name}: {config_path}",
        )
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        return config
    except Exception as e:
        logger.error(f"Error loading scholarship config {config_path}: {e}")
        raise HTTPException(status_code=500, detail="Failed to load scholarship config")


def require_admin(auth_token: Optional[str] = Cookie(None)) -> dict:
    """Admin guard for chat/admin endpoints."""
    token_data = verify_token_with_context(auth_token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if token_data.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return token_data


@app.get("/admin/{scholarship}/weights")
async def get_scholarship_weights(
    scholarship: str,
    _: dict = Depends(require_admin),
):
    """Get current scoring weights for a scholarship from canonical config."""
    config = load_scholarship_config(scholarship)
    agents_cfg = config.get("agents", {})
    scoring_cfg = config.get("scoring", {})
    scoring_agents = scoring_cfg.get("scoring_agents", [])

    weights = {}
    total = 0.0
    for name, agent in agents_cfg.items():
        weight = agent.get("weight")
        if weight is not None:
            weights[name] = {
                "weight": weight,
                "description": agent.get("description", ""),
                "enabled": agent.get("enabled", True),
                "required": agent.get("required", False),
            }
            total += weight

    return {
        "scholarship": scholarship,
        "weights": weights,
        "total_weight": round(total, 4),
        "scoring_agents": scoring_agents,
    }


@app.put("/admin/{scholarship}/weights")
async def update_scholarship_weights(
    scholarship: str,
    payload: Dict[str, Any],
    _: dict = Depends(require_admin),
):
    """Update scoring weights in canonical config and regenerate artifacts."""
    config = load_scholarship_config(scholarship)
    agents_cfg = config.get("agents", {})

    new_weights = payload.get("weights", {})
    if not isinstance(new_weights, dict):
        raise HTTPException(status_code=400, detail="weights must be an object")

    total = 0.0
    for name, w in new_weights.items():
        if name not in agents_cfg:
            raise HTTPException(status_code=400, detail=f"Unknown agent: {name}")
        try:
            weight_val = float(w.get("weight"))
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid weight for agent {name}")
        agents_cfg[name]["weight"] = weight_val
        total += weight_val

    if abs(total - 1.0) > 0.001:
        raise HTTPException(
            status_code=400,
            detail=f"Weights must sum to 1.0, got {total}",
        )

    config["agents"] = agents_cfg

    # Persist back to config.yml with simple backup
    config_path = get_scholarship_config_path(scholarship)
    backup_path = config_path.with_suffix(".backup")
    try:
        import shutil
        import yaml

        if config_path.exists():
            shutil.copy2(config_path, backup_path)
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f, sort_keys=False, allow_unicode=True)
    except Exception as e:
        logger.error(f"Failed to write updated config for {scholarship}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save updated weights")

    # Regenerate artifacts on disk
    try:
        from scripts.generate_scholarship_artifacts import main as generate_main

        root = Path(__file__).resolve().parents[1]
        generate_main([str(root / "scripts/generate_scholarship_artifacts.py"), scholarship])
    except Exception as e:
        logger.error(f"Failed to regenerate artifacts for {scholarship}: {e}")
        raise HTTPException(status_code=500, detail="Weights saved but artifact regeneration failed")

    return {"status": "ok", "total_weight": round(total, 4)}


@app.get("/admin/{scholarship}/criteria/{agent_name}")
async def get_agent_criteria(
    scholarship: str,
    agent_name: str,
    _: dict = Depends(require_admin),
):
    """Get current criteria text for a specific agent from canonical config."""
    config = load_scholarship_config(scholarship)
    agents_cfg = config.get("agents", {})
    criteria_text = config.get("criteria_text", {})

    if agent_name not in agents_cfg:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_name}")

    crit_ref = agents_cfg[agent_name].get("criteria_ref")
    crit_value = criteria_text.get(crit_ref) if crit_ref else None

    return {
        "scholarship": scholarship,
        "agent": agent_name,
        "criteria_ref": crit_ref,
        "criteria_text": crit_value,
    }


@app.put("/admin/{scholarship}/criteria/{agent_name}")
async def update_agent_criteria(
    scholarship: str,
    agent_name: str,
    payload: Dict[str, Any],
    _: dict = Depends(require_admin),
):
    """Update criteria text for a specific agent and regenerate artifacts."""
    config = load_scholarship_config(scholarship)
    agents_cfg = config.get("agents", {})
    criteria_text = config.get("criteria_text", {})

    if agent_name not in agents_cfg:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_name}")

    crit_ref = agents_cfg[agent_name].get("criteria_ref")
    if not crit_ref:
        raise HTTPException(status_code=400, detail=f"Agent {agent_name} does not use criteria_ref")

    new_text = payload.get("criteria_text")
    if not isinstance(new_text, str) or not new_text.strip():
        raise HTTPException(status_code=400, detail="criteria_text must be a non-empty string")

    if len(new_text) < 100:
        raise HTTPException(status_code=400, detail="criteria_text is too short (< 100 characters)")

    criteria_text[crit_ref] = new_text
    config["criteria_text"] = criteria_text

    # Persist back to config.yml with simple backup
    config_path = get_scholarship_config_path(scholarship)
    backup_path = config_path.with_suffix(".backup")
    try:
        import shutil
        import yaml

        if config_path.exists():
            shutil.copy2(config_path, backup_path)
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f, sort_keys=False, allow_unicode=True)
    except Exception as e:
        logger.error(f"Failed to write updated criteria for {scholarship}: {e}")
        raise HTTPException(status_code=500, detail="Failed to save updated criteria")

    # Regenerate artifacts (criteria/*.txt, etc.)
    try:
        from scripts.generate_scholarship_artifacts import main as generate_main

        root = Path(__file__).resolve().parents[1]
        generate_main([str(root / "scripts/generate_scholarship_artifacts.py"), scholarship])
    except Exception as e:
        logger.error(f"Failed to regenerate artifacts for {scholarship}: {e}")
        raise HTTPException(status_code=500, detail="Criteria saved but artifact regeneration failed")

    return {"status": "ok", "agent": agent_name}


@app.post("/admin/{scholarship}/criteria/{agent_name}/regenerate")
async def regenerate_agent_criteria_with_llm(
    scholarship: str,
    agent_name: str,
    payload: Dict[str, Any],
    _: dict = Depends(require_admin),
):
    """Generate a new criteria draft for an agent using an LLM."""
    from beeai_framework.backend.chat import ChatModel  # type: ignore
    from beeai_framework.backend.message import UserMessage  # type: ignore

    config = load_scholarship_config(scholarship)
    agents_cfg = config.get("agents", {})
    criteria_text = config.get("criteria_text", {})

    if agent_name not in agents_cfg:
        raise HTTPException(status_code=404, detail=f"Unknown agent: {agent_name}")

    agent_cfg = agents_cfg[agent_name]
    crit_ref = agent_cfg.get("criteria_ref")
    if not crit_ref:
        raise HTTPException(status_code=400, detail=f"Agent {agent_name} does not use criteria_ref")

    current_text = criteria_text.get(crit_ref, "")
    base_description = payload.get("base_description") or agent_cfg.get("description", "")
    target_model = payload.get("target_model") or os.getenv("PRIMARY_MODEL", "ollama:llama3.2:1b")

    system_prompt = (
        "You are an expert in designing scoring rubrics for scholarship application agents.\n"
        "Generate clear, structured evaluation criteria text suitable to be used as a prompt\n"
        "for an LLM that will score this agent. The output should be plain text with headings\n"
        "and bullet points, not JSON. Do not include instructions about JSON schemas.\n"
    )

    user_prompt_parts = [
        f"Scholarship ID: {scholarship}",
        f"Agent name: {agent_name}",
        f"Agent description: {base_description}",
        f"Target model identifier: {target_model}",
    ]
    if current_text:
        user_prompt_parts.append(
            "Current criteria text (improve and refine, but keep intent compatible):\n"
            f"{current_text}"
        )
    else:
        user_prompt_parts.append("No existing criteria text; create a new rubric from scratch.")

    user_prompt = "\n\n".join(user_prompt_parts)

    try:
        chat_model = ChatModel.from_name(target_model)
        messages = [
            UserMessage(system_prompt),
            UserMessage(user_prompt),
        ]
        result = await chat_model.run(messages)
        new_text = result.last_message.text if result and result.last_message else ""
    except Exception as e:
        logger.error(f"Failed to regenerate criteria with LLM for {scholarship}/{agent_name}: {e}")
        raise HTTPException(status_code=500, detail="LLM criteria generation failed")

    if not new_text or len(new_text) < 100:
        raise HTTPException(status_code=500, detail="Generated criteria text is too short or empty")

    return {
        "scholarship": scholarship,
        "agent": agent_name,
        "criteria_ref": crit_ref,
        "current_criteria_text": current_text,
        "proposed_criteria_text": new_text,
    }


@app.post("/admin/{scholarship}/pipeline/run")
async def trigger_pipeline_rerun(
    scholarship: str,
    payload: Dict[str, Any],
    admin: dict = Depends(require_admin),
):
    """Stub endpoint to trigger a scholarship processing pipeline rerun.

    For now this only validates input and logs the request; it does not
    actually invoke the full workflow.
    """
    max_applicants = payload.get("max_applicants")
    stop_on_error = bool(payload.get("stop_on_error", False))
    skip_processed = bool(payload.get("skip_processed", True))

    if max_applicants is not None:
        try:
            max_int = int(max_applicants)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="max_applicants must be an integer")
        if max_int <= 0:
            raise HTTPException(status_code=400, detail="max_applicants must be positive")
        max_applicants = max_int

    logger.info(
        "Pipeline rerun requested (stub)",
        extra={
            "scholarship": scholarship,
            "max_applicants": max_applicants,
            "stop_on_error": stop_on_error,
            "skip_processed": skip_processed,
            "username": admin.get("username"),
        },
    )

    # TODO: Wire this to the actual scholarship_workflow runner.
    return {
        "status": "stub",
        "detail": "Pipeline trigger accepted (stub only; workflow not yet wired).",
        "scholarship": scholarship,
        "max_applicants": max_applicants,
        "stop_on_error": stop_on_error,
        "skip_processed": skip_processed,
    }


@app.get("/", response_class=HTMLResponse)
async def get_chat_interface(auth_token: Optional[str] = Cookie(None)):
    """Serve the chat interface HTML (requires authentication)."""
    # Check authentication
    username = verify_token(auth_token)
    if not username:
        # Redirect to login
        return Response(
            content='<script>window.location.href="/login";</script>',
            media_type="text/html"
        )
    
    template_path = Path(__file__).parent / "templates" / "chat.html"
    
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            html_content = f.read()
        return HTMLResponse(content=html_content)
    except FileNotFoundError:
        logger.error(f"Template file not found: {template_path}")
        raise HTTPException(status_code=500, detail="Chat interface template not found")


def extract_auth_token_from_cookies(cookie_header: str) -> Optional[str]:
    """Extract auth_token from cookie header string.
    
    Args:
        cookie_header: The cookie header string from the request
        
    Returns:
        The auth token if found, None otherwise
    """
    for cookie in cookie_header.split("; "):
        if cookie.startswith("auth_token="):
            return cookie.split("=", 1)[1]
    return None


async def authenticate_websocket(websocket: WebSocket) -> Optional[dict]:
    """Authenticate WebSocket connection and return full token data.
    
    Args:
        websocket: The WebSocket connection to authenticate
        
    Returns:
        Token data dictionary if authentication successful, None otherwise
    """
    cookie_header = websocket.headers.get("cookie", "")
    auth_token = extract_auth_token_from_cookies(cookie_header)
    token_data = verify_token_with_context(auth_token)
    
    if not token_data:
        # Must accept before closing to avoid 403
        await websocket.accept()
        await websocket.close(code=1008, reason="Unauthorized")
        return None
    
    logger.info(
        f"WebSocket authenticated: {token_data['username']}",
        extra={
            "username": token_data["username"],
            "role": token_data["role"],
            "scholarships": token_data["scholarships"]
        }
    )
    
    return token_data


async def process_chat_message(websocket: WebSocket, message_data: dict, token_data: dict) -> None:
    """Process a chat message with scholarship access control.
    
    Args:
        websocket: The WebSocket connection
        message_data: The parsed message data from the client
        token_data: The authenticated user's token data with scholarship context
    """
    if message_data.get("type") != "message":
        return
    
    user_message = message_data.get("content", "")
    username = token_data["username"]
    
    # Create access control middleware
    access_control = ScholarshipAccessMiddleware(token_data)
    
    # Get accessible scholarships for context
    accessible_scholarships = access_control.get_accessible_scholarships()
    scholarship_names = [s["name"] for s in accessible_scholarships]
    
    # Get the selected scholarship from token (set during scholarship selection)
    selected_scholarship = token_data.get("selected_scholarship")
    
    # Fallback logic if no scholarship selected yet
    if not selected_scholarship:
        scholarship_ids = token_data.get("scholarships", [])
        if scholarship_ids and scholarship_ids[0] != "*":
            selected_scholarship = scholarship_ids[0]
        else:
            selected_scholarship = "Delaney_Wings"  # Default fallback
    
    # Verify user has access to the selected scholarship
    if not access_control.can_access_scholarship(selected_scholarship):
        await websocket.send_json({
            "type": "error",
            "content": f"Access denied to scholarship: {selected_scholarship}. Please select a valid scholarship."
        })
        return
    
    # Add scholarship context to agent instructions
    scholarship_context = f"""
User Context:
- Username: {token_data['username']}
- Role: {token_data['role']}
- Scholarship: {selected_scholarship}
- Permissions: {', '.join(token_data['permissions'])}

IMPORTANT: When calling API endpoints, you MUST use the scholarship parameter with the value: "{selected_scholarship}"
All API calls require a 'scholarship' query parameter. Use "{selected_scholarship}" for all requests.

You can only access and provide information about the scholarships listed above.
If the user asks about other scholarships, politely inform them they don't have access.
"""
    
    # Structured logging with context
    log_context = {
        "username": username,
        "role": token_data["role"],
        "selected_scholarship": selected_scholarship,
        "message_length": len(user_message),
        "timestamp": time.time()
    }
    logger.info(
        "Processing chat message",
        extra=log_context
    )
    
    # Metrics: Track execution time
    start_time = time.time()
    
    try:
        if agent_handler is None:
            raise RuntimeError("Agent handler not initialized")
        
        # Get the agent from the handler (works for both multi-agent and single-agent modes)
        agent = agent_handler.get_agent()
        
        # Validate inputs before processing
        if not user_message or not user_message.strip():
            raise ValueError("User message cannot be empty")

        # Build contextualized message with clear separation
        contextualized_message = "\n\n".join([
            scholarship_context.strip(),
            f"User Query: {user_message.strip()}"
        ])
        # Log message preparation (detailed logging already done above)
        logger.debug(
            "Message contextualized",
            extra={
                "query_length": len(user_message),
                "context_length": len(scholarship_context),
                "total_length": len(contextualized_message)
            }
        )

        try:
            agent_run = agent.run(contextualized_message)
            
            # Add event logging
            agent_run = agent_run.observe(
                lambda emitter: emitter.on(
                    "update",
                    lambda data, event: logger.info(
                        f"Event {event.path} triggered by {type(event.creator).__name__}",
                        extra={"username": username, "event_path": event.path}
                    )
                )
            )
            
            # Execute with timeout
            response = await asyncio.wait_for(
                agent_run,
                timeout=300.0  # 5 minute timeout
            )
        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            logger.error(
                f"Agent execution timeout for user {username}",
                extra={**log_context, "execution_time": execution_time, "status": "timeout"}
            )
            raise RuntimeError("Request timed out. Please try again with a simpler query.")
        
        # Response validation: Check if response structure is valid
        if not response:
            raise RuntimeError("Agent returned empty response")
        
        if not hasattr(response, 'last_message'):
            raise AttributeError("Response missing 'last_message' attribute")
        
        if not response.last_message:
            raise RuntimeError("Agent returned no messages")
        
        if not hasattr(response.last_message, 'text'):
            raise AttributeError("Response message missing 'text' attribute")
        
        agent_response = response.last_message.text
        
        if not agent_response or not agent_response.strip():
            logger.warning(f"Agent returned empty text for user {username}", extra=log_context)
            agent_response = "I apologize, but I couldn't generate a response. Please try rephrasing your question."
        
        # Optional: Include which agent handled the request for transparency
        handling_agent = getattr(response, 'agent_name', 'orchestrator')
        
        # Metrics: Calculate and log execution time
        execution_time = time.time() - start_time
        logger.info(
            f"Response from {handling_agent} for {username}",
            extra={
                **log_context,
                "execution_time": execution_time,
                "response_length": len(agent_response),
                "handling_agent": handling_agent,
                "status": "success"
            }
        )

        await websocket.send_json({
            "type": "response",
            "message": agent_response,
            "agent": handling_agent,  # For debugging/transparency
            "execution_time": round(execution_time, 2)  # Include timing for client-side metrics
        })
        
    except asyncio.TimeoutError:
        # Already logged above, just send error to client
        await websocket.send_json({
            "type": "error",
            "message": "Request timed out. Please try again with a simpler query."
        })
    except (AttributeError, RuntimeError) as e:
        execution_time = time.time() - start_time
        logger.error(
            f"Invalid response structure for {username}: {e}",
            extra={**log_context, "execution_time": execution_time, "status": "error", "error_type": type(e).__name__}
        )
        await websocket.send_json({
            "type": "error",
            "message": "An error occurred processing your request. Please try again."
        })
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(
            f"Error processing message for {username}: {e}",
            extra={**log_context, "execution_time": execution_time, "status": "error", "error_type": type(e).__name__},
            exc_info=True
        )
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for chat communication (requires authentication)."""
    # Authenticate the connection
    token_data = await authenticate_websocket(websocket)
    if not token_data:
        return
    
    await websocket.accept()
    logger.debug(f"WebSocket connection established for user: {token_data['username']}")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Process the message
            await process_chat_message(websocket, message_data, token_data)
    
    except WebSocketDisconnect:
        logger.debug(f"WebSocket disconnected for user: {token_data['username']}")
    except Exception as e:
        logger.error(f"WebSocket error for {token_data['username']}: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": "Connection error occurred"
            })
        except:
            pass  # Connection already closed


@app.get("/api/user/profile")
async def get_user_profile(auth_token: Optional[str] = Cookie(None)):
    """Get current user's profile information."""
    token_data = verify_token_with_context(auth_token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    access_control = ScholarshipAccessMiddleware(token_data)
    scholarships = access_control.get_accessible_scholarships()
    
    # Get observability dashboard URL for admin users
    observability_dashboard = None
    if token_data["role"] == "admin":
        observability_dashboard = os.environ.get("OBSERVABILITY_DASHBOARD", "")
    
    return {
        "username": token_data["username"],
        "role": token_data["role"],
        "scholarships": scholarships,
        "permissions": token_data["permissions"],
        "observability_dashboard": observability_dashboard
    }


@app.get("/api/user/scholarships")
async def get_user_scholarships_endpoint(auth_token: Optional[str] = Cookie(None)):
    """Get scholarships accessible to current user."""
    token_data = verify_token_with_context(auth_token)
    if not token_data:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    access_control = ScholarshipAccessMiddleware(token_data)
    # Return list directly for the selection page
    return access_control.get_accessible_scholarships()


@app.get("/health")
async def health_check():
    """Health check endpoint with agent status."""
    if agent_handler is None:
        return {
            "status": "initializing",
            "agent_mode": AGENT_MODE,
            "chat_model": CHAT_MODEL
        }
    
    # Get status from the agent handler
    status_info = agent_handler.get_status()
    
    return {
        "status": "healthy",
        "agent_mode": AGENT_MODE,
        **status_info
    }


def main():
    """Main entry point for running the chat server.
    
    Supports multiple agent modes and model providers via environment variables:
    - AGENT_MODE: Agent architecture mode (multi or single, default: multi)
    - CHAT_MODEL: Main model for agent responses
    - ORCHESTRATOR_MODEL: Model for routing in multi-agent mode (optional, defaults to CHAT_MODEL)
    
    Examples:
        # Multi-agent mode with Anthropic Claude (default)
        CHAT_MODEL="anthropic:claude-sonnet-4-20250514" python -m bee_agents.chat_api
        
        # Single-agent mode with Ollama
        AGENT_MODE=single CHAT_MODEL="ollama/llama3.2:3b" python -m bee_agents.chat_api
        
        # Multi-agent with fast orchestrator, quality responses
        ORCHESTRATOR_MODEL="ollama/llama3.2:1b" CHAT_MODEL="anthropic:claude-sonnet-4-20250514" python -m bee_agents.chat_api
    """
    parser = argparse.ArgumentParser(
        description="Scholarship Agent Chat Server - Multi-Mode & Multi-Model Support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Agent Mode Configuration:
  Set via environment variables:
    AGENT_MODE           Agent architecture (multi or single, default: multi)
                         - multi: Multi-agent orchestration with specialized agents
                         - single: Single unified agent handling all tasks
    
Model Configuration:
  Set via environment variables:
    CHAT_MODEL           Main model for responses (default: anthropic:claude-sonnet-4-20250514)
    ORCHESTRATOR_MODEL   Model for routing in multi-agent mode (default: same as CHAT_MODEL)
  
  Supported providers:
    - Anthropic: anthropic:claude-sonnet-4-20250514
    - Ollama:    ollama/llama3.2:3b, ollama/llama3:8b, ollama/qwen2.5:7b
    - OpenAI:    openai:gpt-4, openai:gpt-3.5-turbo
        """
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8100,
        help="Port to bind to (default: 8100)"
    )
    parser.add_argument(
        "--ssl-keyfile",
        type=str,
        default="key.pem",
        help="Path to SSL key file for HTTPS (default: key.pem)"
    )
    parser.add_argument(
        "--ssl-certfile",
        type=str,
        default="cert.pem",
        help="Path to SSL certificate file for HTTPS (default: cert.pem)"
    )
    
    args = parser.parse_args()
    
    # Run the server
    import uvicorn
    from uvicorn.config import LOGGING_CONFIG
    import os
    
    # Check if SSL certificates exist
    ssl_keyfile = None
    ssl_certfile = None
    if os.path.exists(args.ssl_keyfile) and os.path.exists(args.ssl_certfile):
        ssl_keyfile = args.ssl_keyfile
        ssl_certfile = args.ssl_certfile
    
    protocol = "https" if ssl_keyfile and ssl_certfile else "http"
    logger.info(f"Starting chat server on {protocol}://{args.host}:{args.port}")
    logger.info(f"Agent mode: {AGENT_MODE}")
    logger.info(f"Chat model: {CHAT_MODEL}")
    if AGENT_MODE == "multi":
        logger.info(f"Orchestrator model: {ORCHESTRATOR_MODEL}")
    logger.info(f"Open {protocol}://localhost:{args.port} in your browser")
    
    if ssl_keyfile and ssl_certfile:
        logger.info(f"SSL enabled with keyfile: {ssl_keyfile}")
        logger.info(f"SSL certificate: {ssl_certfile}")
    else:
        logger.info("SSL disabled (no certificates found)")
    
    # Configure uvicorn logging to match our format and suppress WebSocket noise
    log_config = LOGGING_CONFIG.copy()
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Suppress noisy WebSocket connection logs
    log_config["loggers"]["uvicorn.error"]["level"] = "WARNING"
    log_config["loggers"]["uvicorn.access"]["level"] = "WARNING"
    
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_config=log_config,
        ssl_keyfile=ssl_keyfile,
        ssl_certfile=ssl_certfile
    )


if __name__ == "__main__":
    main()

# Made with Bob

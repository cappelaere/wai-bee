"""FastAPI chat interface for the scholarship agent.

This module provides a web-based chat interface for interacting with
the scholarship agent using WebSockets for real-time communication.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-08
Version: 1.0.0
License: MIT

Example:
    Run the chat server::
    
        python bee_agents/chat_api.py --port 8100
"""

import asyncio
import os, json
import logging
import time
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager
import argparse

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Cookie
from fastapi.responses import HTMLResponse, FileResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles

from beeai_framework.backend import ChatModel  # type: ignore
from beeai_framework.agents.requirement import RequirementAgent  # type: ignore
from beeai_framework.tools.openapi import OpenAPITool  # type: ignore
from beeai_framework.memory import UnconstrainedMemory
from beeai_framework.tools.handoff import HandoffTool
from beeai_framework.middleware.trajectory import GlobalTrajectoryMiddleware

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

# Configure logging
logger = setup_logging('chat')

# Global agent instances
orchestrator_agent: Optional[RequirementAgent] = None
scholarship_agent: Optional[RequirementAgent] = None
review_agent: Optional[RequirementAgent] = None  # Placeholder for future
model_name: str = os.environ.get("CHAT_MODEL", "anthropic:claude-sonnet-4-20250514")


async def initialize_scholarship_agent(llm: ChatModel) -> RequirementAgent:
    """Initialize the scholarship agent with OpenAPI tools.
    
    Args:
        llm: The language model to use
        
    Returns:
        Initialized scholarship agent with OpenAPI tools
    """
    logger.info("Initializing scholarship agent...")
    
    # Load OpenAPI schema
    schema_path = Path(__file__).parent / "openapi.json"
    try:
        with open(schema_path) as f:
            open_api_schema = json.load(f)
    except FileNotFoundError:
        logger.error(f"OpenAPI schema not found at {schema_path}")
        raise
    
    # Create tools from OpenAPI schema
    tools = OpenAPITool.from_schema(open_api_schema)
    logger.info(f"Scholarship agent: Loaded {len(tools)} OpenAPI tools")
    
    # Create specialized agent
    return RequirementAgent(
        llm=llm,
        tools=tools,
        name="ScholarshipAgent",
        description="Specialized agent for scholarship requirement analysis and queries"
    )


async def initialize_review_agent(llm: ChatModel) -> Optional[RequirementAgent]:
    """Initialize the application review agent.
    
    Args:
        llm: The language model to use
        
    Returns:
        Initialized review agent, or None if not yet implemented
    """
    # TODO: Implement when review agent is ready
    logger.info("Review agent: Not yet implemented")
    return None


async def initialize_orchestrator_agent(
    llm: ChatModel,
    scholarship_agent: Optional[RequirementAgent],
    review_agent: Optional[RequirementAgent]
) -> RequirementAgent:
    """Initialize the main orchestrator agent with hand-off capabilities.
    
    Args:
        llm: The language model to use
        scholarship_agent: The scholarship specialist agent (if available)
        review_agent: The review specialist agent (if available)
        
    Returns:
        Initialized orchestrator agent
    """
    logger.info("Initializing orchestrator agent...")
    
    # Build handoff tools dynamically based on available agents
    handoff_tools = []
    
    if scholarship_agent:
        handoff_tools.append(
            HandoffTool(
                target=scholarship_agent,
                name="scholarship_specialist",
                description="Answers questions about current scores and scholarship applications"
            )
        )
    
    if review_agent:
        handoff_tools.append(
            HandoffTool(
                target=review_agent,
                name="review_expert",
                description="Review a specific application to provide a second opinion and provide feedback"
            )
        )
    
    # Build instructions based on available agents
    instructions_parts = ["You are the main coordinator agent."]
    
    if scholarship_agent:
        instructions_parts.append("- For scholarship related questions or queries: use the scholarship_specialist")
    
    if review_agent:
        instructions_parts.append("- For review related questions or queries: use the review_expert")
    
    instructions_parts.append("- For general questions: answer directly")
    instructions_parts.append("\nAlways be helpful and explain which specialist will help if delegating.")
    
    instructions = "\n".join(instructions_parts)
    
    # The orchestrator can delegate to specialized agents using BeeAI's hand-off pattern
    return RequirementAgent(
        llm=llm,
        memory=UnconstrainedMemory(),
        tools=handoff_tools,
        instructions=instructions,
        name="OrchestratorAgent",
        description="Main coordinator agent that routes requests to specialized agents"
    )


async def initialize_agents():
    """Initialize all agents with multi-agent orchestration."""
    global orchestrator_agent, scholarship_agent, review_agent
    
    logger.info("Initializing multi-agent system...")
    
    # Initialize shared LLM
    llm = ChatModel.from_name(model_name)
    logger.info(f"Using model: {model_name}")
    
    # Initialize specialized agents
    scholarship_agent = await initialize_scholarship_agent(llm)
    review_agent = await initialize_review_agent(llm)
    
    # Count active agents
    active_agents = sum([1 for agent in [scholarship_agent, review_agent] if agent is not None])
    
    # Initialize orchestrator with specialized agents
    orchestrator_agent = await initialize_orchestrator_agent(llm, scholarship_agent, review_agent)
    
    logger.info(f"Multi-agent system initialized with {active_agents} specialized agent(s)")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
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
        if orchestrator_agent is None:
            raise RuntimeError("Orchestrator agent not initialized")
        
        # Use orchestrator with timeout protection - it will handle delegation to specialized agents
        # Prepend scholarship context to the message
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
            response = await asyncio.wait_for( orchestrator_agent
                .run(contextualized_message)
                #.middleware(GlobalTrajectoryMiddleware())
                .observe(
                    lambda emitter: emitter.on(
                        "update",
                        lambda data, event: logger.info(
                            f"Event {event.path} triggered by {type(event.creator).__name__}",
                            extra={"username": username, "event_path": event.path}
                        )
                    )
                ),
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
    logger.info(f"WebSocket connection established for user: {token_data['username']}")
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Process the message
            await process_chat_message(websocket, message_data, token_data)
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for user: {token_data['username']}")
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
    
    return {
        "username": token_data["username"],
        "role": token_data["role"],
        "scholarships": scholarships,
        "permissions": token_data["permissions"]
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
    """Health check endpoint with multi-agent status."""
    return {
        "status": "healthy",
        "orchestrator_initialized": orchestrator_agent is not None,
        "agents": {
            "scholarship": scholarship_agent is not None,
            "review": review_agent is not None
        },
        "model": model_name
    }


def main():
    """Main entry point for running the chat server."""
    parser = argparse.ArgumentParser(description="Scholarship Agent Chat Server")
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
        "--model",
        type=str,
        default="anthropic:claude-sonnet-4-20250514",
        help="Model to use (default: anthropic:claude-sonnet-4-20250514)"
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
    
    global model_name
    model_name = args.model
    
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
    logger.info(f"Using model: {model_name}")
    logger.info(f"Open {protocol}://localhost:{args.port} in your browser")
    
    if ssl_keyfile and ssl_certfile:
        logger.info(f"SSL enabled with keyfile: {ssl_keyfile}")
        logger.info(f"SSL certificate: {ssl_certfile}")
    else:
        logger.info("SSL disabled (no certificates found)")
    
    # Configure uvicorn logging to match our format
    log_config = LOGGING_CONFIG.copy()
    log_config["formatters"]["default"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_config["formatters"]["access"]["fmt"] = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
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

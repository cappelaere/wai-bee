"""Single-agent implementation for scholarship chat system.

This module provides a simplified single-agent implementation without orchestration,
where one agent handles all tasks directly with all available tools.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-12
Version: 1.0.0
License: MIT
"""
import asyncio
import time
from fastapi import WebSocket

import os
import json
import logging
from pathlib import Path
from typing import Optional

from beeai_framework.backend import ChatModel  # type: ignore
from beeai_framework.agents.requirement import RequirementAgent  # type: ignore
from beeai_framework.tools.openapi import OpenAPITool  # type: ignore
from beeai_framework.memory import UnconstrainedMemory
from beeai_framework.cache import SlidingCache
from beeai_framework.errors import FrameworkError
from beeai_framework.backend import ChatModelParameters, UserMessage

from .logging_config import setup_logging

logger = setup_logging('chat_agents_single')

# Shared cache for response caching across all instances (not actively used yet)
response_cache: SlidingCache[str] = SlidingCache(size=100)


class SingleAgentHandler:
    """Single-agent handler that processes all requests with one unified agent."""
    
    def __init__(self, chat_model: str):
        """Initialize the single-agent handler.
        
        Args:
            chat_model: Model name for the agent (e.g., "anthropic:claude-sonnet-4-20250514")
        """
        self.chat_model = chat_model
        self.agent: Optional[RequirementAgent] = None
        
        logger.info(f"SingleAgentHandler initialized with chat_model={chat_model}")
    
    async def initialize_agent(self, llm: ChatModel) -> RequirementAgent:
        """Initialize the single unified agent with all tools.
        
        Args:
            llm: The language model to use
            
        Returns:
            Initialized agent with all available tools
        """
        logger.info("Initializing single unified agent...")
        
        # Load OpenAPI schema
        schema_path = Path(__file__).parent / "openapi.json"
        try:
            with open(schema_path) as f:
                open_api_schema = json.load(f)
        except FileNotFoundError:
            logger.error(f"OpenAPI schema not found at {schema_path}")
            raise
        
        # Override server URL from environment if set (for Docker networking)
        api_server_url = os.environ.get("API_SERVER_URL")
        if api_server_url:
            # Update the server URL in the schema
            if "servers" in open_api_schema and len(open_api_schema["servers"]) > 0:
                open_api_schema["servers"][0]["url"] = api_server_url.rstrip('/')
                logger.info(f"Using API server URL from environment: {api_server_url}")
        
        # Create tools from OpenAPI schema
        # TODO Should we add ThinkTool() to the tools to reason
        self.open_api_schema = open_api_schema
        tools = OpenAPITool.from_schema(self.open_api_schema)
        logger.info(f"Single agent: Loaded {len(tools)} OpenAPI tools")
        
        # Create comprehensive instructions for the single agent
        instructions = """You are a comprehensive scholarship assistant agent.

Your responsibilities include:
1. Answering questions about scholarship requirements and criteria
2. Analyzing scholarship applications and providing scores
3. Retrieving application data and statistics
4. Providing insights and recommendations

You have access to all the necessary tools to:
- Query scholarship criteria and requirements
- Retrieve applicant information and scores
- Analyze applications and provide detailed feedback
- Generate statistics and reports

Always:
- Use the appropriate tools to get accurate information
- Provide clear, helpful responses
- Explain your reasoning when analyzing applications
- Be professional and supportive in your communication

When calling API endpoints, always use the scholarship parameter provided in the user context.
"""
        
        # Create single unified agent with all tools
        return RequirementAgent(
            llm=llm,
            tools=tools,
            memory=UnconstrainedMemory(),
            instructions=instructions,
            name="ScholarshipAssistant",
            description="Unified agent for all scholarship-related tasks and queries"
        )
    
    async def initialize(self):
        """Initialize the single agent.
        
        Supports multiple model providers:
        - Anthropic: anthropic:claude-sonnet-4-20250514
        - Ollama: ollama/llama3.2:3b, ollama/qwen2.5:7b
        - OpenAI: openai:gpt-4, openai:gpt-3.5-turbo
        """
        logger.info("Initializing single-agent system...")
        logger.info(f"Chat model: {self.chat_model}")
        
        
        # Initialize model
        llm = ChatModel.from_name(self.chat_model)
        # Caching does not seem to work for RequirementAgent 
        #llm.config(parameters=ChatModelParameters(max_tokens=1000), cache=SlidingCache(size=50))

        # Initialize the single agent with all tools
        self.agent = await self.initialize_agent(llm)
        
        logger.info("Single-agent system initialized successfully")
    
    def get_agent(self) -> RequirementAgent:
        """Get the main agent for processing messages.
        
        Returns:
            The unified agent
            
        Raises:
            RuntimeError: If agent not initialized
        """
        if self.agent is None:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
        return self.agent
    
    def get_status(self) -> dict:
        """Get status of the agent.
        
        Returns:
            Dictionary with agent status information
        """
        return {
            "agent_initialized": self.agent is not None,
            "mode": "single-agent",
            "chat_model": self.chat_model
        }
    
    def _extract_auth_token_from_cookies(self, cookie_header: str) -> Optional[str]:
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
    
    async def _authenticate_websocket(self, websocket: WebSocket) -> Optional[dict]:
        """Authenticate WebSocket connection and return full token data.
        
        Args:
            websocket: The WebSocket connection to authenticate
            
        Returns:
            Token data dictionary if authentication successful, None otherwise
        """
        from .auth import verify_token_with_context
        
        cookie_header = websocket.headers.get("cookie", "")
        auth_token = self._extract_auth_token_from_cookies(cookie_header)
        token_data = verify_token_with_context(auth_token)
        
        if not token_data:
            await websocket.send_json({
                "type": "error",
                "content": "Unauthorized - please log in"
            })
            return None
        
        # Attach raw token (which may be empty) so downstream logic can forward it
        token_data.setdefault("token", auth_token or "")
        
        logger.info(f"WebSocket authenticated: {token_data['username']}")
        logger.info(f"WebSocket token: {token_data['token']}")
        
        return token_data
    
    async def process_message(self, websocket: WebSocket, message_data: dict) -> None:
        """Process a chat message with scholarship access control.
        
        Args:
            websocket: The WebSocket connection
            message_data: The parsed message data from the client
        """
        # Authenticate the websocket connection
        token_data = await self._authenticate_websocket(websocket)
        if not token_data:
            return
        
        if message_data.get("type") != "message":
            return
        
        user_message = message_data.get("content", "")
        username = token_data["username"]
        
        # Import middleware here to avoid circular dependencies
        from .middleware import ScholarshipAccessMiddleware
        
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
- token: {token_data['token']}
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
        logger.info("Processing chat message")
        
        # Metrics: Track execution time
        start_time = time.time()
        
        try:
            if self.agent is None:
                raise RuntimeError("Agent not initialized")
            
            # Validate inputs before processing
            if not user_message or not user_message.strip():
                raise ValueError("User message cannot be empty")

            # Build contextualized message with clear separation
            contextualized_message = "\n\n".join([
                scholarship_context.strip(),
                f"User Query: {user_message.strip()}"
            ])

            try:
                # Check cache first using the shared module-level cache
                hash_key = str(hash(contextualized_message))
                cached_response = await response_cache.get(hash_key)
                if cached_response:
                    logger.info(f"Cached response found for {hash_key}")
                    await websocket.send_json({
                        "type": "response",
                        "message": cached_response,
                        "agent": "cache",
                        "execution_time": 0
                    })
                    return
                
                auth_headers = {"Authorization": f"Bearer {token_data['token']}"}

                agent_run = self.agent.run(contextualized_message)
                
                # Execute with timeout
                response = await asyncio.wait_for(
                    agent_run,
                    timeout=60.0  # 1 minute timeout
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
            await response_cache.set(hash_key, agent_response)
            logger.info(f"Caching response for {hash_key}")

            if not agent_response or not agent_response.strip():
                logger.warning(f"Agent returned empty text for user {username}", extra=log_context)
                agent_response = "I apologize, but I couldn't generate a response. Please try rephrasing your question."
            
            # Optional: Include which agent handled the request for transparency
            handling_agent = getattr(response, 'agent_name', 'single-agent')
            
            # Metrics: Calculate and log execution time
            execution_time = time.time() - start_time
            logger.info(
                f"Response from {handling_agent} for {username} time: {execution_time}")

            # Send a single response back to the client
            await websocket.send_json({
                "type": "response",
                "message": agent_response,
                "agent": handling_agent,
                "execution_time": round(execution_time, 2),
            })
            
        except asyncio.TimeoutError:
            # Already logged above, just send error to client
            await websocket.send_json({
                "type": "error",
                "message": "Request timed out. Please try again with a simpler query."
            })
        except (AttributeError, RuntimeError) as e:
            execution_time = time.time() - start_time
            logger.exception(f"Invalid response structure for {username}: {e}")
            await websocket.send_json({
                "type": "error",
                "message": "An error occurred processing your request. Please try again."
            })
        except Exception as e:
            execution_time = time.time() - start_time
            logger.exception(f"Error processing message for {username}")
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })

# Made with Bob

"""Multi-agent orchestration for scholarship chat system.

This module provides the multi-agent implementation with orchestrator pattern
and specialized agents for different tasks.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-12
Version: 1.0.0
License: MIT
"""

import os
import json
import logging
import asyncio
import time
from pathlib import Path
from typing import Optional

from fastapi import WebSocket
from beeai_framework.backend import ChatModel  # type: ignore
from beeai_framework.agents.requirement import RequirementAgent  # type: ignore
from beeai_framework.tools.openapi import OpenAPITool  # type: ignore
from beeai_framework.memory import UnconstrainedMemory
from beeai_framework.tools.handoff import HandoffTool
from beeai_framework.cache import SlidingCache

from .logging_config import setup_logging

logger = setup_logging('chat_agents')

# Shared cache for response caching across all instances
response_cache: SlidingCache[str] = SlidingCache(size=100)


class MultiAgentOrchestrator:
    """Multi-agent orchestrator with specialized agents and hand-off capabilities."""
    
    def __init__(self, chat_model: str, orchestrator_model: Optional[str] = None):
        """Initialize the multi-agent orchestrator.
        
        Args:
            chat_model: Model name for specialized agents (e.g., "anthropic:claude-sonnet-4-20250514")
            orchestrator_model: Model name for orchestrator (defaults to chat_model)
        """
        self.chat_model = chat_model
        self.orchestrator_model = orchestrator_model or chat_model
        
        self.orchestrator_agent: Optional[RequirementAgent] = None
        self.scholarship_agent: Optional[RequirementAgent] = None
        self.review_agent: Optional[RequirementAgent] = None
        
        logger.info(f"MultiAgentOrchestrator initialized with chat_model={chat_model}, orchestrator_model={self.orchestrator_model}")
    
    async def initialize_scholarship_agent(self, llm: ChatModel) -> RequirementAgent:
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
    
    async def initialize_review_agent(self, llm: ChatModel) -> Optional[RequirementAgent]:
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
        self,
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
    
    async def initialize(self):
        """Initialize all agents with multi-agent orchestration.
        
        Supports multiple model providers:
        - Anthropic: anthropic:claude-sonnet-4-20250514
        - Ollama: ollama/llama3.2:3b, ollama/qwen2.5:7b
        - OpenAI: openai:gpt-4, openai:gpt-3.5-turbo
        """
        logger.info("Initializing multi-agent system...")
        logger.info(f"Chat model: {self.chat_model}")
        logger.info(f"Orchestrator model: {self.orchestrator_model}")
        
        # Initialize models - can use different models for different agents
        chat_llm = ChatModel.from_name(self.chat_model)
        orchestrator_llm = ChatModel.from_name(self.orchestrator_model) if self.orchestrator_model != self.chat_model else chat_llm
        
        # Initialize specialized agents with chat model (for quality)
        self.scholarship_agent = await self.initialize_scholarship_agent(chat_llm)
        self.review_agent = await self.initialize_review_agent(chat_llm)
        
        # Count active agents
        active_agents = sum([1 for agent in [self.scholarship_agent, self.review_agent] if agent is not None])
        
        # Initialize orchestrator with potentially faster model (for routing)
        self.orchestrator_agent = await self.initialize_orchestrator_agent(
            orchestrator_llm, 
            self.scholarship_agent, 
            self.review_agent
        )
        
        logger.info(f"Multi-agent system initialized with {active_agents} specialized agent(s)")
    
    def get_agent(self) -> RequirementAgent:
        """Get the main orchestrator agent for processing messages.
        
        Returns:
            The orchestrator agent
            
        Raises:
            RuntimeError: If agents not initialized
        """
        if self.orchestrator_agent is None:
            raise RuntimeError("Agents not initialized. Call initialize() first.")
        return self.orchestrator_agent
    
    def get_status(self) -> dict:
        """Get status of all agents.
        
        Returns:
            Dictionary with agent status information
        """
        return {
            "orchestrator_initialized": self.orchestrator_agent is not None,
            "agents": {
                "scholarship": self.scholarship_agent is not None,
                "review": self.review_agent is not None
            },
            "chat_model": self.chat_model,
            "orchestrator_model": self.orchestrator_model
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
        
        logger.info(
            f"WebSocket authenticated: {token_data['username']}",
            extra={
                "username": token_data["username"],
                "role": token_data["role"],
                "scholarships": token_data["scholarships"]
            }
        )
        
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
            if self.orchestrator_agent is None:
                raise RuntimeError("Orchestrator agent not initialized")
            
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
                
                agent_run = self.orchestrator_agent.run(contextualized_message)
                
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
            handling_agent = getattr(response, 'agent_name', 'orchestrator')
            
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
            logger.error(f"Invalid response structure for {username}: {e}")
            await websocket.send_json({
                "type": "error",
                "message": "An error occurred processing your request. Please try again."
            })
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Error processing message for {username}: {e}")
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })

# Made with Bob

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
from pathlib import Path
from typing import Optional

from beeai_framework.backend import ChatModel  # type: ignore
from beeai_framework.agents.requirement import RequirementAgent  # type: ignore
from beeai_framework.tools.openapi import OpenAPITool  # type: ignore
from beeai_framework.memory import UnconstrainedMemory
from beeai_framework.tools.handoff import HandoffTool

from .logging_config import setup_logging

logger = setup_logging('chat_agents')


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

# Made with Bob

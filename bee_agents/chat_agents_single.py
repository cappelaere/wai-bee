"""Single-agent implementation for scholarship chat system.

This module provides a simplified single-agent implementation without orchestration,
where one agent handles all tasks directly with all available tools.

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
from beeai_framework.cache import SlidingCache
from beeai_framework.errors import FrameworkError
from beeai_framework.backend import ChatModelParameters, UserMessage

from .logging_config import setup_logging

logger = setup_logging('chat_agents_single')


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
        
        # Create tools from OpenAPI schema
        # TODO Should we add ThinkTool() to the tools to reason
        tools = OpenAPITool.from_schema(open_api_schema)
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

# Made with Bob

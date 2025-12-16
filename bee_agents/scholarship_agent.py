"""Interactive Scholarship Agent using BeeAI Framework.

This module provides an interactive agent that can query scholarship data
using the OpenAPI-based tools and natural language.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-08
Version: 1.0.0
License: MIT

Example:
    Run the interactive agent::
    
        python bee_agents/scholarship_agent.py
"""

# https://framework.beeai.dev

import asyncio
import json
import logging
import os
import sys
import traceback
from typing import Optional

from aiofiles import open as aio_open
from dotenv import load_dotenv
from rich.console import Console
from rich.markdown import Markdown

from beeai_framework.backend import ChatModel
from beeai_framework.agents.requirement import RequirementAgent
from beeai_framework.errors import FrameworkError
from beeai_framework.tools.openapi import OpenAPITool

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ScholarshipAgent:
    """Interactive agent for querying scholarship data."""
    
    def __init__(self, model_name: str = "ollama:granite3.3:8b", schema_path: Optional[str] = None, render_markdown: bool = True):
        """Initialize the scholarship agent.
        
        Args:
            model_name: Name of the LLM model to use
            schema_path: Path to OpenAPI schema file (defaults to openapi.json in current dir)
            render_markdown: Whether to render responses as markdown (default: True)
        """
        self.model_name = model_name
        self.schema_path = schema_path or os.path.join(os.path.dirname(__file__), "openapi.json")
        self.agent: Optional[RequirementAgent] = None
        self.tools = []
        self.render_markdown = render_markdown
        self.console = Console() if render_markdown else None
        
    async def initialize(self) -> None:
        """Initialize the agent by loading schema and creating tools."""
        logger.info("Initializing Scholarship Agent", extra={
            "model": self.model_name,
            "schema_path": self.schema_path
        })
        
        # Load OpenAPI schema
        try:
            async with aio_open(self.schema_path) as file:
                content = await file.read()
                open_api_schema = json.loads(content)
        except FileNotFoundError:
            logger.error(f"OpenAPI schema not found: {self.schema_path}")
            raise FileNotFoundError(
                f"OpenAPI schema not found at {self.schema_path}. "
                "Run: python -m bee_agents.generate_openapi"
            )
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in schema file: {e}")
            raise ValueError(f"Invalid JSON in schema file: {e}")
        
        # Initialize LLM
        try:
            llm = ChatModel.from_name(self.model_name)
        except Exception as e:
            logger.error(f"Failed to initialize model '{self.model_name}': {e}")
            raise RuntimeError(f"Failed to initialize model '{self.model_name}': {e}")
        
        # Create tools from OpenAPI schema
        self.tools = OpenAPITool.from_schema(open_api_schema)
        logger.info(f"Loaded {len(self.tools)} tools from OpenAPI schema", extra={
            "tool_count": len(self.tools),
            "tools": [tool.name for tool in self.tools]
        })
        
        # Create agent
        self.agent = RequirementAgent(llm=llm, tools=self.tools)
        logger.info("Agent initialized successfully")
    
    async def query(self, prompt: str) -> str:
        """Query the agent with a prompt.
        
        Args:
            prompt: User's question or request
            
        Returns:
            Agent's response text
        """
        if not self.agent:
            raise RuntimeError("Agent not initialized. Call initialize() first.")
        
        response = await self.agent.run(prompt)
        return response.last_message.text
    
    async def interactive_loop(self) -> None:
        """Run an interactive loop for continuous conversation."""
        logger.info("Starting interactive mode")
        
        # Print welcome message (keep for user interaction)
        print("=" * 80)
        print("🎓 Scholarship Agent - Interactive Mode")
        print("=" * 80)
        print()
        print("Ask questions about scholarship applications!")
        print("Examples:")
        print("  - List top 5 scholars")
        print("  - Show me statistics for all applications")
        print("  - Get details for application 75179")
        print("  - What is the average score?")
        print()
        print("Commands:")
        print("  - 'quit' or 'exit' to exit")
        print("  - 'help' for examples")
        print("  - 'tools' to list available tools")
        print()
        print("=" * 80)
        print()
        
        while True:
            try:
                # Get user input
                user_input = input("You: ").strip()
                
                # Handle empty input
                if not user_input:
                    continue
                
                # Handle commands
                if user_input.lower() in ['quit', 'exit', 'q']:
                    logger.info("User exited interactive mode")
                    print("\n👋 Goodbye!")
                    break
                
                if user_input.lower() == 'help':
                    self._print_help()
                    continue
                
                if user_input.lower() == 'tools':
                    self._print_tools()
                    continue
                
                # Query the agent
                print()
                response = await self.query(user_input)
                
                # Render response
                if self.render_markdown and self.console:
                    print("🤖 Agent:")
                    print()
                    md = Markdown(response)
                    self.console.print(md)
                else:
                    print("🤖 Agent: ", end="", flush=True)
                    print(response)
                print()
                
            except KeyboardInterrupt:
                logger.info("Interactive mode interrupted by user")
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                logger.exception("Error during query processing")
                print(f"\n❌ Error: {e}")
                print()
    
    def _print_help(self) -> None:
        """Print help information."""
        print()
        print("📚 Example Questions:")
        print("  - List top 5 scholars")
        print("  - Show me the top 10 applications")
        print("  - Get statistics for all applications")
        print("  - What is the average score?")
        print("  - Show me details for application 75179")
        print("  - Get the score for WAI number 101127")
        print("  - How many applications are there?")
        print("  - Show me applications with scores above 90")
        print()
    
    def _print_tools(self) -> None:
        """Print available tools."""
        print()
        print(f"🔧 Available Tools ({len(self.tools)}):")
        for tool in self.tools:
            print(f"   - {tool.name}")
        print()


async def main() -> None:
    """Main entry point for the interactive agent."""
    # Create and initialize agent
    # modelName = "ollama:llama3.2:3b"
    modelName = "anthropic:claude-sonnet-4-20250514"

    agent = ScholarshipAgent(
        model_name=modelName,
        schema_path=None,  # Uses default path
        render_markdown=True  # Enable markdown rendering
    )
    
    try:
        await agent.initialize()
        await agent.interactive_loop()
    except FrameworkError as e:
        logger.error(f"Framework error: {e}", exc_info=True)
        print(f"\n❌ Framework Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception("Unexpected error in main")
        print(f"\n❌ Unexpected Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        print("\n\n👋 Goodbye!")
        sys.exit(0)

# Made with Bob

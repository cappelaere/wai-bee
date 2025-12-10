"""Orchestrator Agent for coordinating specialized agents.

This is the main agent that receives user queries, determines intent,
and routes to the appropriate specialized agent.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-07
"""

import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

from dotenv import load_dotenv
from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_core.tools import Tool
from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

from .results_agent import ResultsRetrievalAgent
from .explanation_agent import ScoreExplanationAgent
from .file_agent import FileRetrievalAgent

# Load environment variables
load_dotenv()


class OrchestratorAgent:
    """Main orchestrator that coordinates specialized agents."""
    
    def __init__(self, outputs_dir: Path = Path("outputs"),
                 model: Optional[str] = None):
        """Initialize the Orchestrator Agent.
        
        Args:
            outputs_dir: Base outputs directory.
            model: Ollama model to use. If None, uses ORCHESTRATOR_MODEL from .env.
        """
        self.logger = logging.getLogger(__name__)
        self.outputs_dir = outputs_dir
        
        # Load model from env if not provided
        if model is None:
            model = os.getenv('ORCHESTRATOR_MODEL', 'llama3.2:3b')
            # Remove 'ollama/' prefix if present
            if model.startswith('ollama/'):
                model = model.replace('ollama/', '')
        
        self.model = model
        self.logger.info(f"Orchestrator using model: {model}")
        
        # Initialize LLM
        self.llm = OllamaLLM(model=model, temperature=0.1)
        
        # Initialize specialized agents
        self.results_agent = ResultsRetrievalAgent(outputs_dir, model)
        self.explanation_agent = ScoreExplanationAgent(outputs_dir, model)
        self.file_agent = FileRetrievalAgent(outputs_dir, model)
        
        # Create tools
        self.tools = self._create_tools()
        
        # Create orchestrator agent
        self.agent = self._create_agent()
        
        # Conversation history
        self.history: list[Dict[str, str]] = []
    
    def _create_tools(self) -> list[Tool]:
        """Create tools that delegate to specialized agents.
        
        Returns:
            List of Tool objects.
        """
        tools = [
            Tool(
                name="query_results",
                func=lambda query: self._query_results_wrapper(query),
                description="""Use this tool for questions about applicant data, rankings, statistics, or searching.
                Examples:
                - "How many applicants are there?"
                - "Who are the top 5 applicants?"
                - "What's John Smith's score?"
                - "Show me applicant WAI 127830"
                Input: The user's question about results/data."""
            ),
            Tool(
                name="explain_scores",
                func=lambda query: self._explain_scores_wrapper(query),
                description="""Use this tool for questions about WHY an applicant received a certain score.
                Examples:
                - "Why did WAI 127830 get a low application score?"
                - "Explain the recommendation score for applicant 112222"
                - "What validation errors does WAI 127830 have?"
                Input: The user's question about score explanations."""
            ),
            Tool(
                name="retrieve_files",
                func=lambda query: self._retrieve_files_wrapper(query),
                description="""Use this tool for questions about accessing original files or attachments.
                Examples:
                - "List attachments for WAI 127830"
                - "Where is the resume for applicant 112222?"
                - "Show me the processing summary for WAI 127830"
                Input: The user's question about files."""
            )
        ]
        
        return tools
    
    def _query_results_wrapper(self, query: str) -> str:
        """Delegate to Results Retrieval Agent.
        
        Args:
            query: User's question.
            
        Returns:
            Agent's response.
        """
        try:
            self.logger.info(f"Delegating to Results Agent: {query}")
            return self.results_agent.query(query)
        except Exception as e:
            self.logger.error(f"Error in results agent: {e}")
            return f"Error querying results: {str(e)}"
    
    def _explain_scores_wrapper(self, query: str) -> str:
        """Delegate to Score Explanation Agent.
        
        Args:
            query: User's question.
            
        Returns:
            Agent's response.
        """
        try:
            self.logger.info(f"Delegating to Explanation Agent: {query}")
            return self.explanation_agent.query(query)
        except Exception as e:
            self.logger.error(f"Error in explanation agent: {e}")
            return f"Error explaining scores: {str(e)}"
    
    def _retrieve_files_wrapper(self, query: str) -> str:
        """Delegate to File Retrieval Agent.
        
        Args:
            query: User's question.
            
        Returns:
            Agent's response.
        """
        try:
            self.logger.info(f"Delegating to File Agent: {query}")
            return self.file_agent.query(query)
        except Exception as e:
            self.logger.error(f"Error in file agent: {e}")
            return f"Error retrieving files: {str(e)}"
    
    def _create_agent(self) -> AgentExecutor:
        """Create the orchestrator agent.
        
        Returns:
            AgentExecutor instance.
        """
        template = """You are an intelligent assistant that helps users query scholarship application results.

CONTEXT: All queries are for the scholarship mentioned in the question. If no scholarship is specified, assume it's in the question context.

You have access to the following tools:

{tools}

You coordinate three specialized agents:
- query_results: For data queries, rankings, statistics, searching applicants
- explain_scores: For explaining WHY applicants received certain scores
- retrieve_files: For accessing original files and attachments

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

IMPORTANT RULES:
1. When a tool returns a complete answer to the user's question, that IS your Final Answer
2. Do NOT call additional tools or continue processing after getting a complete answer
3. Simply return the tool's response as your Final Answer
4. The scholarship context is already in the question - do not ask for it again

Begin!

Question: {input}
Thought:{agent_scratchpad}"""

        prompt = PromptTemplate.from_template(template)
        
        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=3,  # Reduced from 5 to prevent loops
            handle_parsing_errors=True,
            early_stopping_method="force"  # Force stop after max iterations
        )
        
        return agent_executor
    
    def chat(self, message: str, scholarship: str = "Delaney_Wings") -> str:
        """Process a chat message.
        
        Args:
            message: User's message.
            scholarship: Scholarship name (default: "Delaney_Wings").
            
        Returns:
            Agent's response.
        """
        try:
            # Add scholarship context if not present
            if scholarship.lower() not in message.lower():
                message = f"{message} (Scholarship: {scholarship})"
            
            # Format history for prompt
            history_str = "\n".join([
                f"User: {h['user']}\nAssistant: {h['assistant']}"
                for h in self.history[-3:]  # Last 3 exchanges
            ])
            
            # Invoke agent
            result = self.agent.invoke({
                "input": message,
                "history": history_str
            })
            
            response = result.get("output", "I couldn't process that request.")
            
            # Update history
            self.history.append({
                "user": message,
                "assistant": response
            })
            
            return response
        except Exception as e:
            self.logger.error(f"Error in orchestrator: {e}")
            return f"I encountered an error: {str(e)}"
    
    def reset_history(self):
        """Clear conversation history."""
        self.history = []
        self.logger.info("Conversation history cleared")


# Made with Bob
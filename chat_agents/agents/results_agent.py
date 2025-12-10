"""Results Retrieval Agent for querying scholarship data.

This agent handles queries about applicant data, rankings, and statistics.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-07
"""

import logging
from pathlib import Path
from typing import Dict, Any, List

from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_core.tools import Tool
from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

from ..tools.data_tools import ScholarshipDataTools


class ResultsRetrievalAgent:
    """Agent for retrieving and querying scholarship results data."""
    
    def __init__(self, outputs_dir: Path = Path("outputs"), 
                 model: str = "llama3.2:3b"):
        """Initialize the Results Retrieval Agent.
        
        Args:
            outputs_dir: Base outputs directory.
            model: Ollama model to use.
        """
        self.logger = logging.getLogger(__name__)
        self.data_tools = ScholarshipDataTools(outputs_dir)
        self.model = model
        
        # Initialize LLM
        self.llm = OllamaLLM(model=model, temperature=0.1)
        
        # Create tools
        self.tools = self._create_tools()
        
        # Create agent
        self.agent = self._create_agent()
    
    def _create_tools(self) -> List[Tool]:
        """Create LangChain tools for the agent.
        
        Returns:
            List of Tool objects.
        """
        tools = [
            Tool(
                name="get_applicant_by_wai",
                func=lambda query: self._get_applicant_wrapper(query),
                description="""Get detailed information about a specific applicant by WAI number.
                Input should be: 'WAI_NUMBER|SCHOLARSHIP' (e.g., '127830|Delaney_Wings')
                Returns applicant's name, scores, location, and completion status."""
            ),
            Tool(
                name="search_by_name",
                func=lambda query: self._search_name_wrapper(query),
                description="""Search for applicants by name (partial match, case-insensitive).
                Input should be: 'NAME|SCHOLARSHIP' (e.g., 'John|Delaney_Wings')
                Returns list of matching applicants with their WAI numbers and scores."""
            ),
            Tool(
                name="get_top_applicants",
                func=lambda query: self._get_top_wrapper(query),
                description="""Get top N applicants by score.
                Input should be: 'N|SCHOLARSHIP|SCORE_TYPE' (e.g., '10|Delaney_Wings|final_score')
                Score types: final_score, application_score, recommendation_score, academic_score, essay_score
                Returns ranked list of top applicants."""
            ),
            Tool(
                name="get_statistics",
                func=lambda query: self._get_stats_wrapper(query),
                description="""Get summary statistics for a scholarship.
                Input should be: 'SCHOLARSHIP' (e.g., 'Delaney_Wings')
                Returns total applicants, averages, and score ranges."""
            )
        ]
        
        return tools
    
    def _get_applicant_wrapper(self, query: str) -> str:
        """Wrapper for get_applicant_by_wai tool.
        
        Args:
            query: Format "WAI_NUMBER|SCHOLARSHIP"
            
        Returns:
            Formatted string with applicant data.
        """
        try:
            parts = query.split('|')
            if len(parts) != 2:
                return "Error: Input must be 'WAI_NUMBER|SCHOLARSHIP'"
            
            wai_number, scholarship = parts
            wai_number = wai_number.strip().strip("'\"")
            scholarship = scholarship.strip().strip("'\"")
            result = self.data_tools.get_applicant_by_wai(wai_number.strip(), scholarship.strip())
            
            if result is None:
                return f"Applicant WAI {wai_number} not found in {scholarship}"
            
            # Format the result
            output = f"""Applicant Information:
- WAI Number: {result.get('wai_number')}
- Name: {result.get('name')}
- Location: {result.get('city')}, {result.get('state') or result.get('country')}
- Rank: {result.get('rank')}
- Final Score: {result.get('final_score'):.2f}
- Application Score: {result.get('application_score'):.2f}
- Recommendation Score: {result.get('recommendation_score'):.2f}
- Academic Score: {result.get('academic_score'):.2f}
- Essay Score: {result.get('essay_score'):.2f}
- Complete: {'Yes' if result.get('complete') else 'No'}"""
            
            return output
        except Exception as e:
            self.logger.error(f"Error in get_applicant_wrapper: {e}")
            return f"Error retrieving applicant data: {str(e)}"
    
    def _search_name_wrapper(self, query: str) -> str:
        """Wrapper for search_by_name tool.
        
        Args:
            query: Format "NAME|SCHOLARSHIP"
            
        Returns:
            Formatted string with search results.
        """
        try:
            parts = query.split('|')
            if len(parts) != 2:
                return "Error: Input must be 'NAME|SCHOLARSHIP'"
            
            name, scholarship = parts
            name = name.strip().strip("'\"")
            scholarship = scholarship.strip().strip("'\"")
            results = self.data_tools.search_by_name(name.strip(), scholarship.strip())
            
            if not results:
                return f"No applicants found matching '{name}' in {scholarship}"
            
            # Format results
            output = f"Found {len(results)} applicant(s) matching '{name}':\n\n"
            for i, applicant in enumerate(results, 1):
                output += f"{i}. {applicant.get('name')} (WAI {applicant.get('wai_number')})\n"
                output += f"   Final Score: {applicant.get('final_score'):.2f}, Rank: {applicant.get('rank')}\n"
            
            return output
        except Exception as e:
            self.logger.error(f"Error in search_name_wrapper: {e}")
            return f"Error searching by name: {str(e)}"
    
    def _get_top_wrapper(self, query: str) -> str:
        """Wrapper for get_top_applicants tool.
        
        Args:
            query: Format "N|SCHOLARSHIP|SCORE_TYPE"
            
        Returns:
            Formatted string with top applicants.
        """
        try:
            # Remove leading/trailing quotes if present
            query = query.strip().strip("'\"")
            
            parts = query.split('|')
            if len(parts) < 2:
                return "Error: Input must be 'N|SCHOLARSHIP' or 'N|SCHOLARSHIP|SCORE_TYPE'"
            
            # Strip quotes and whitespace from each part
            n = int(parts[0].strip().strip("'\""))
            scholarship = parts[1].strip().strip("'\"")
            score_type = parts[2].strip().strip("'\"") if len(parts) > 2 else "final_score"
            
            results = self.data_tools.get_top_applicants(n, scholarship, score_type)
            
            if not results:
                return f"No applicants found in {scholarship}"
            
            # Format results
            output = f"Top {len(results)} applicants by {score_type}:\n\n"
            for i, applicant in enumerate(results, 1):
                output += f"{i}. {applicant.get('name')} (WAI {applicant.get('wai_number')})\n"
                output += f"   {score_type}: {applicant.get(score_type):.2f}\n"
                output += f"   Final Score: {applicant.get('final_score'):.2f}\n\n"
            
            return output
        except Exception as e:
            self.logger.error(f"Error in get_top_wrapper: {e}")
            return f"Error getting top applicants: {str(e)}"
    
    def _get_stats_wrapper(self, query: str) -> str:
        """Wrapper for get_statistics tool.
        
        Args:
            query: Scholarship name
            
        Returns:
            Formatted string with statistics.
        """
        try:
            scholarship = query.strip().strip("'\"")
            stats = self.data_tools.get_statistics(scholarship)
            
            if stats is None:
                return f"No statistics available for {scholarship}"
            
            # Format statistics
            output = f"""Statistics for {scholarship}:

Total Applicants: {stats['total_applicants']}
Complete Applications: {stats['complete_applications']}

Average Scores:
- Final Score: {stats['average_scores']['final_score']:.2f}
- Application: {stats['average_scores']['application_score']:.2f}
- Recommendation: {stats['average_scores']['recommendation_score']:.2f}
- Academic: {stats['average_scores']['academic_score']:.2f}
- Essay: {stats['average_scores']['essay_score']:.2f}

Score Range (Final):
- Minimum: {stats['score_ranges']['final_score']['min']:.2f}
- Maximum: {stats['score_ranges']['final_score']['max']:.2f}"""
            
            return output
        except Exception as e:
            self.logger.error(f"Error in get_stats_wrapper: {e}")
            return f"Error getting statistics: {str(e)}"
    
    def _create_agent(self) -> AgentExecutor:
        """Create the LangChain agent.
        
        Returns:
            AgentExecutor instance.
        """
        # Define the prompt template
        template = """Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}"""

        prompt = PromptTemplate.from_template(template)
        
        # Create the agent
        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        # Create executor
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=5,
            handle_parsing_errors=True
        )
        
        return agent_executor
    
    def query(self, question: str, scholarship: str = "Delaney_Wings") -> str:
        """Process a query about scholarship results.
        
        Args:
            question: User's question.
            scholarship: Scholarship name (default: "Delaney_Wings").
            
        Returns:
            Agent's response.
        """
        try:
            # Add scholarship context to the question if not already present
            if scholarship.lower() not in question.lower():
                question = f"{question} (Scholarship: {scholarship})"
            
            result = self.agent.invoke({"input": question})
            return result.get("output", "I couldn't process that query.")
        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            return f"Error: {str(e)}"


# Made with Bob
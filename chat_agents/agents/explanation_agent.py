"""Score Explanation Agent for analyzing and explaining scores.

This agent handles queries about why applicants received certain scores
and provides detailed breakdowns of scoring components.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-07
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, List

from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_core.tools import Tool
from langchain_core.prompts import PromptTemplate
from langchain_ollama import OllamaLLM

from ..tools.data_tools import ScholarshipDataTools


class ScoreExplanationAgent:
    """Agent for explaining applicant scores and providing detailed analysis."""
    
    def __init__(self, outputs_dir: Path = Path("outputs"), 
                 model: str = "llama3.2:3b"):
        """Initialize the Score Explanation Agent.
        
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
                name="explain_application_score",
                func=lambda query: self._explain_application_wrapper(query),
                description="""Explain the application score for an applicant.
                Input should be: 'WAI_NUMBER|SCHOLARSHIP' (e.g., '127830|Delaney_Wings')
                Returns detailed breakdown of completeness, validity, and attachment scores."""
            ),
            Tool(
                name="explain_recommendation_score",
                func=lambda query: self._explain_recommendation_wrapper(query),
                description="""Explain the recommendation score for an applicant.
                Input should be: 'WAI_NUMBER|SCHOLARSHIP'
                Returns analysis of recommendation letters and scoring breakdown."""
            ),
            Tool(
                name="explain_academic_score",
                func=lambda query: self._explain_academic_wrapper(query),
                description="""Explain the academic/resume score for an applicant.
                Input should be: 'WAI_NUMBER|SCHOLARSHIP'
                Returns analysis of academic achievements and qualifications."""
            ),
            Tool(
                name="explain_essay_score",
                func=lambda query: self._explain_essay_wrapper(query),
                description="""Explain the essay score for an applicant.
                Input should be: 'WAI_NUMBER|SCHOLARSHIP'
                Returns analysis of essay quality and scoring breakdown."""
            ),
            Tool(
                name="get_validation_errors",
                func=lambda query: self._get_validation_errors_wrapper(query),
                description="""Get validation errors for an applicant's application.
                Input should be: 'WAI_NUMBER|SCHOLARSHIP'
                Returns list of validation errors if any exist."""
            )
        ]
        
        return tools
    
    def _explain_application_wrapper(self, query: str) -> str:
        """Explain application score.
        
        Args:
            query: Format "WAI_NUMBER|SCHOLARSHIP"
            
        Returns:
            Formatted explanation.
        """
        try:
            # Remove leading/trailing quotes if present
            query = query.strip().strip("'\"")
            
            parts = query.split('|')
            if len(parts) != 2:
                return "Error: Input must be 'WAI_NUMBER|SCHOLARSHIP'"
            
            # Strip quotes and whitespace from each part
            wai_number = parts[0].strip().strip("'\"")
            scholarship = parts[1].strip().strip("'\"")
            
            analysis = self.data_tools.load_analysis_file(
                wai_number, scholarship, "application"
            )
            
            if analysis is None:
                return f"Application analysis not found for WAI {wai_number}"
            
            # Extract scoring information
            scores = analysis.get('scores', {})
            score_breakdown = analysis.get('score_breakdown', {})
            
            output = f"""Application Score Explanation for WAI {wai_number}:

Overall Score: {scores.get('overall_score', 0):.2f}/100

Score Breakdown:
1. Completeness ({score_breakdown.get('completeness', {}).get('weight', 30)}%): {score_breakdown.get('completeness', {}).get('score', 0):.2f}
   - Required fields present and valid
   
2. Validity ({score_breakdown.get('validity', {}).get('weight', 30)}%): {score_breakdown.get('validity', {}).get('score', 0):.2f}
   - Data quality and format validation
   
3. Attachments ({score_breakdown.get('attachments', {}).get('weight', 40)}%): {score_breakdown.get('attachments', {}).get('score', 0):.2f}
   - Required documents present and valid

"""
            
            # Add validation errors if present
            if analysis.get('has_errors'):
                output += "\nValidation Errors:\n"
                for error in analysis.get('validation_errors', []):
                    output += f"- {error}\n"
            
            return output
        except Exception as e:
            self.logger.error(f"Error explaining application score: {e}")
            return f"Error: {str(e)}"
    
    def _explain_recommendation_wrapper(self, query: str) -> str:
        """Explain recommendation score.
        
        Args:
            query: Format "WAI_NUMBER|SCHOLARSHIP"
            
        Returns:
            Formatted explanation.
        """
        try:
            # Remove leading/trailing quotes if present
            query = query.strip().strip("'\"")
            
            parts = query.split('|')
            if len(parts) != 2:
                return "Error: Input must be 'WAI_NUMBER|SCHOLARSHIP'"
            
            # Strip quotes and whitespace from each part
            wai_number = parts[0].strip().strip("'\"")
            scholarship = parts[1].strip().strip("'\"")
            
            analysis = self.data_tools.load_analysis_file(
                wai_number, scholarship, "recommendation"
            )
            
            if analysis is None:
                return f"Recommendation analysis not found for WAI {wai_number}"
            
            scores = analysis.get('scores', {})
            
            output = f"""Recommendation Score Explanation for WAI {wai_number}:

Overall Score: {scores.get('overall_score', 0):.2f}/100

Summary: {analysis.get('summary', 'No summary available')}

Key Strengths:
"""
            for strength in analysis.get('profile_features', {}).get('strengths', []):
                output += f"- {strength}\n"
            
            output += "\nAreas for Improvement:\n"
            for area in analysis.get('profile_features', {}).get('areas_for_improvement', []):
                output += f"- {area}\n"
            
            return output
        except Exception as e:
            self.logger.error(f"Error explaining recommendation score: {e}")
            return f"Error: {str(e)}"
    
    def _explain_academic_wrapper(self, query: str) -> str:
        """Explain academic score.
        
        Args:
            query: Format "WAI_NUMBER|SCHOLARSHIP"
            
        Returns:
            Formatted explanation.
        """
        try:
            # Remove leading/trailing quotes if present
            query = query.strip().strip("'\"")
            
            parts = query.split('|')
            if len(parts) != 2:
                return "Error: Input must be 'WAI_NUMBER|SCHOLARSHIP'"
            
            # Strip quotes and whitespace from each part
            wai_number = parts[0].strip().strip("'\"")
            scholarship = parts[1].strip().strip("'\"")
            
            analysis = self.data_tools.load_analysis_file(
                wai_number, scholarship, "academic"
            )
            
            if analysis is None:
                return f"Academic analysis not found for WAI {wai_number}"
            
            scores = analysis.get('scores', {})
            
            output = f"""Academic Score Explanation for WAI {wai_number}:

Overall Score: {scores.get('overall_score', 0):.2f}/100

Summary: {analysis.get('summary', 'No summary available')}

Key Qualifications:
"""
            for qual in analysis.get('profile_features', {}).get('strengths', []):
                output += f"- {qual}\n"
            
            return output
        except Exception as e:
            self.logger.error(f"Error explaining academic score: {e}")
            return f"Error: {str(e)}"
    
    def _explain_essay_wrapper(self, query: str) -> str:
        """Explain essay score.
        
        Args:
            query: Format "WAI_NUMBER|SCHOLARSHIP"
            
        Returns:
            Formatted explanation.
        """
        try:
            # Remove leading/trailing quotes if present
            query = query.strip().strip("'\"")
            
            parts = query.split('|')
            if len(parts) != 2:
                return "Error: Input must be 'WAI_NUMBER|SCHOLARSHIP'"
            
            # Strip quotes and whitespace from each part
            wai_number = parts[0].strip().strip("'\"")
            scholarship = parts[1].strip().strip("'\"")
            
            analysis = self.data_tools.load_analysis_file(
                wai_number, scholarship, "essay"
            )
            
            if analysis is None:
                return f"Essay analysis not found for WAI {wai_number}"
            
            scores = analysis.get('scores', {})
            
            output = f"""Essay Score Explanation for WAI {wai_number}:

Overall Score: {scores.get('overall_score', 0):.2f}/100

Summary: {analysis.get('summary', 'No summary available')}

Strengths:
"""
            for strength in analysis.get('profile_features', {}).get('strengths', []):
                output += f"- {strength}\n"
            
            output += "\nAreas for Improvement:\n"
            for area in analysis.get('profile_features', {}).get('areas_for_improvement', []):
                output += f"- {area}\n"
            
            return output
        except Exception as e:
            self.logger.error(f"Error explaining essay score: {e}")
            return f"Error: {str(e)}"
    
    def _get_validation_errors_wrapper(self, query: str) -> str:
        """Get validation errors.
        
        Args:
            query: Format "WAI_NUMBER|SCHOLARSHIP"
            
        Returns:
            Formatted list of errors.
        """
        try:
            # Remove leading/trailing quotes if present
            query = query.strip().strip("'\"")
            
            parts = query.split('|')
            if len(parts) != 2:
                return "Error: Input must be 'WAI_NUMBER|SCHOLARSHIP'"
            
            # Strip quotes and whitespace from each part
            wai_number = parts[0].strip().strip("'\"")
            scholarship = parts[1].strip().strip("'\"")
            
            app_data = self.data_tools.get_application_data(
                wai_number, scholarship
            )
            
            if app_data is None:
                return f"Application data not found for WAI {wai_number}"
            
            if not app_data.get('has_errors'):
                return f"No validation errors found for WAI {wai_number}"
            
            output = f"Validation Errors for WAI {wai_number}:\n\n"
            for error in app_data.get('validation_errors', []):
                output += f"- {error}\n"
            
            return output
        except Exception as e:
            self.logger.error(f"Error getting validation errors: {e}")
            return f"Error: {str(e)}"
    
    def _create_agent(self) -> AgentExecutor:
        """Create the LangChain agent.
        
        Returns:
            AgentExecutor instance.
        """
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
        
        agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        agent_executor = AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=5,
            handle_parsing_errors=True
        )
        
        return agent_executor
    
    def query(self, question: str, scholarship: str = "Delaney_Wings") -> str:
        """Process a query about scores.
        
        Args:
            question: User's question.
            scholarship: Scholarship name.
            
        Returns:
            Agent's response.
        """
        try:
            if scholarship.lower() not in question.lower():
                question = f"{question} (Scholarship: {scholarship})"
            
            result = self.agent.invoke({"input": question})
            return result.get("output", "I couldn't process that query.")
        except Exception as e:
            self.logger.error(f"Error processing query: {e}")
            return f"Error: {str(e)}"


# Made with Bob
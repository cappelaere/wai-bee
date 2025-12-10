"""File Retrieval Agent for accessing original documents.

This agent handles requests for original application files, attachments,
and processing summaries.

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


class FileRetrievalAgent:
    """Agent for retrieving and listing original application files."""
    
    def __init__(self, outputs_dir: Path = Path("outputs"), 
                 model: str = "llama3.2:3b"):
        """Initialize the File Retrieval Agent.
        
        Args:
            outputs_dir: Base outputs directory.
            model: Ollama model to use.
        """
        self.logger = logging.getLogger(__name__)
        self.data_tools = ScholarshipDataTools(outputs_dir)
        self.model = model
        self.outputs_dir = outputs_dir
        
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
                name="list_attachments",
                func=lambda query: self._list_attachments_wrapper(query),
                description="""List all attachment files for an applicant.
                Input should be: 'WAI_NUMBER|SCHOLARSHIP' (e.g., '127830|Delaney_Wings')
                Returns list of attachment filenames (recommendations, resume, essays)."""
            ),
            Tool(
                name="get_attachment_path",
                func=lambda query: self._get_attachment_path_wrapper(query),
                description="""Get the file path for a specific attachment.
                Input should be: 'WAI_NUMBER|SCHOLARSHIP|FILENAME'
                Returns the full path to the attachment file."""
            ),
            Tool(
                name="get_processing_summary",
                func=lambda query: self._get_processing_summary_wrapper(query),
                description="""Get the attachment processing summary for an applicant.
                Input should be: 'WAI_NUMBER|SCHOLARSHIP'
                Returns information about PII removal and file processing."""
            ),
            Tool(
                name="get_application_file_path",
                func=lambda query: self._get_application_path_wrapper(query),
                description="""Get the path to the application data JSON file.
                Input should be: 'WAI_NUMBER|SCHOLARSHIP'
                Returns the path to application_data.json."""
            )
        ]
        
        return tools
    
    def _list_attachments_wrapper(self, query: str) -> str:
        """List attachments for an applicant.
        
        Args:
            query: Format "WAI_NUMBER|SCHOLARSHIP"
            
        Returns:
            Formatted list of attachments.
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
            
            attachments = self.data_tools.list_attachments(
                wai_number, scholarship
            )
            
            if not attachments:
                return f"No attachments found for WAI {wai_number}"
            
            output = f"Attachments for WAI {wai_number}:\n\n"
            
            # Categorize attachments
            recommendations = [f for f in attachments if '_19_' in f and f.endswith(('1.txt', '2.txt'))]
            resume = [f for f in attachments if '_19_3.txt' in f]
            essays = [f for f in attachments if '_1_' in f and f.endswith(('4.txt', '5.txt'))]
            other = [f for f in attachments if f not in recommendations + resume + essays]
            
            if recommendations:
                output += "Recommendations:\n"
                for f in recommendations:
                    output += f"  - {f}\n"
            
            if resume:
                output += "\nResume:\n"
                for f in resume:
                    output += f"  - {f}\n"
            
            if essays:
                output += "\nEssays:\n"
                for f in essays:
                    output += f"  - {f}\n"
            
            if other:
                output += "\nOther:\n"
                for f in other:
                    output += f"  - {f}\n"
            
            return output
        except Exception as e:
            self.logger.error(f"Error listing attachments: {e}")
            return f"Error: {str(e)}"
    
    def _get_attachment_path_wrapper(self, query: str) -> str:
        """Get path to a specific attachment.
        
        Args:
            query: Format "WAI_NUMBER|SCHOLARSHIP|FILENAME"
            
        Returns:
            File path.
        """
        try:
            # Remove leading/trailing quotes if present
            query = query.strip().strip("'\"")
            
            parts = query.split('|')
            if len(parts) != 3:
                return "Error: Input must be 'WAI_NUMBER|SCHOLARSHIP|FILENAME'"
            
            wai_number, scholarship, filename = [p.strip().strip("'\"") for p in parts]
            
            file_path = self.outputs_dir / scholarship / wai_number / "attachments" / filename
            
            if not file_path.exists():
                return f"File not found: {filename}"
            
            return f"File path: {file_path}\nFile size: {file_path.stat().st_size} bytes"
        except Exception as e:
            self.logger.error(f"Error getting attachment path: {e}")
            return f"Error: {str(e)}"
    
    def _get_processing_summary_wrapper(self, query: str) -> str:
        """Get processing summary for attachments.
        
        Args:
            query: Format "WAI_NUMBER|SCHOLARSHIP"
            
        Returns:
            Formatted processing summary.
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
            
            summary = self.data_tools.get_processing_summary(
                wai_number, scholarship
            )
            
            if summary is None:
                return f"Processing summary not found for WAI {wai_number}"
            
            output = f"""Attachment Processing Summary for WAI {wai_number}:

Total Files Processed: {summary.get('summary', {}).get('total_files', 0)}
Total Original Characters: {summary.get('summary', {}).get('total_original_chars', 0):,}
Total Redacted Characters: {summary.get('summary', {}).get('total_redacted_chars', 0):,}
Reduction: {summary.get('summary', {}).get('reduction_percentage', 0):.1f}%

PII Types Found: {', '.join(summary.get('summary', {}).get('pii_types_found', []))}

Processed Files:
"""
            
            for file_info in summary.get('processed_files', []):
                output += f"\n- {file_info.get('source_file')}\n"
                output += f"  Output: {file_info.get('output_file')}\n"
                output += f"  Size: {file_info.get('original_length'):,} → {file_info.get('redacted_length'):,} chars\n"
                if file_info.get('has_errors'):
                    output += f"  Errors: {', '.join(file_info.get('errors', []))}\n"
            
            return output
        except Exception as e:
            self.logger.error(f"Error getting processing summary: {e}")
            return f"Error: {str(e)}"
    
    def _get_application_path_wrapper(self, query: str) -> str:
        """Get path to application data file.
        
        Args:
            query: Format "WAI_NUMBER|SCHOLARSHIP"
            
        Returns:
            File path.
        """
        try:
            parts = query.split('|')
            if len(parts) != 2:
                return "Error: Input must be 'WAI_NUMBER|SCHOLARSHIP'"
            
            wai_number, scholarship = parts
            file_path = self.outputs_dir / scholarship.strip() / wai_number.strip() / "application_data.json"
            
            if not file_path.exists():
                return f"Application data file not found for WAI {wai_number}"
            
            return f"Application data path: {file_path}\nFile size: {file_path.stat().st_size} bytes"
        except Exception as e:
            self.logger.error(f"Error getting application path: {e}")
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
        """Process a query about files.
        
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
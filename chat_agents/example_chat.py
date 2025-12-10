"""Example script demonstrating the chat agent system.

This script shows how to use the orchestrator agent to query
scholarship application results.

Author: Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-07
"""

import logging
from pathlib import Path

from agents.orchestrator import OrchestratorAgent

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    """Run example chat interactions."""
    
    print("="*60)
    print("Scholarship Results Chat Agent")
    print("="*60)
    print()
    
    # Initialize orchestrator
    print("Initializing chat agent...")
    orchestrator = OrchestratorAgent(
        outputs_dir=Path("../outputs")
        # model will be loaded from ORCHESTRATOR_MODEL in .env
    )
    print("✓ Agent ready!\n")
    
    # Example queries
    queries = [
        "How many applicants are there in Delaney_Wings?",
        "Show me the top 5 applicants",
        "Tell me about WAI 127830",
        "Why did WAI 127830 get their application score?",
        "List the attachments for WAI 127830"
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n{'='*60}")
        print(f"Query {i}: {query}")
        print(f"{'='*60}\n")
        
        response = orchestrator.chat(query, scholarship="Delaney_Wings")
        print(f"Response:\n{response}\n")
    
    # Interactive mode
    print("\n" + "="*60)
    print("Interactive Mode (type 'quit' to exit)")
    print("="*60 + "\n")
    
    while True:
        try:
            user_input = input("\nYou: ").strip()
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            if not user_input:
                continue
            
            response = orchestrator.chat(user_input, scholarship="Delaney_Wings")
            print(f"\nAssistant: {response}")
            
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"\nError: {e}")


if __name__ == "__main__":
    main()


# Made with Bob
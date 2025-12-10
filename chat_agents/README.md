# Scholarship Results Chat Agent System

An intelligent chat system for querying scholarship application results using LangChain agents and Ollama LLMs.

## Overview

This system provides a conversational interface to query scholarship application data, explain scores, and retrieve original documents. It uses a multi-agent architecture where specialized agents handle different types of queries.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Query                                │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│              Orchestrator Agent                              │
│  (Routes queries to appropriate specialized agent)           │
└────────┬────────────────┬────────────────┬──────────────────┘
         │                │                │
         ▼                ▼                ▼
┌────────────────┐ ┌──────────────┐ ┌────────────────┐
│ Results Agent  │ │ Explanation  │ │  File Agent    │
│                │ │    Agent     │ │                │
│ - Statistics   │ │ - Score      │ │ - List files   │
│ - Rankings     │ │   breakdown  │ │ - Get paths    │
│ - Search       │ │ - Validation │ │ - Processing   │
│ - Applicant    │ │   errors     │ │   summaries    │
│   data         │ │ - Detailed   │ │                │
│                │ │   analysis   │ │                │
└────────────────┘ └──────────────┘ └────────────────┘
         │                │                │
         └────────────────┴────────────────┘
                          │
                          ▼
                ┌──────────────────┐
                │  Data Tools      │
                │  - CSV reader    │
                │  - JSON loader   │
                │  - File access   │
                └──────────────────┘
```

## Components

### 1. Orchestrator Agent (`agents/orchestrator.py`)
- Main entry point for user queries
- Determines query intent
- Routes to appropriate specialized agent
- Maintains conversation history

### 2. Results Retrieval Agent (`agents/results_agent.py`)
- Queries applicant data from CSV
- Provides statistics and rankings
- Searches by name or WAI number
- Returns formatted results

**Example queries:**
- "How many applicants are there?"
- "Show me the top 10 applicants"
- "What's John Smith's score?"
- "Tell me about WAI 127830"

### 3. Score Explanation Agent (`agents/explanation_agent.py`)
- Explains why applicants received certain scores
- Provides detailed score breakdowns
- Shows validation errors
- Analyzes scoring components

**Example queries:**
- "Why did WAI 127830 get a low application score?"
- "Explain the recommendation score for applicant 112222"
- "What validation errors does WAI 127830 have?"

### 4. File Retrieval Agent (`agents/file_agent.py`)
- Lists available attachments
- Provides file paths
- Shows processing summaries
- Categorizes files (recommendations, resume, essays)

**Example queries:**
- "List attachments for WAI 127830"
- "Where is the resume for applicant 112222?"
- "Show me the processing summary for WAI 127830"

### 5. Data Tools (`tools/data_tools.py`)
- Low-level data access functions
- CSV and JSON file readers
- File system operations
- Used by all agents

## Installation

1. **Install dependencies:**
```bash
# From project root
pip install -r requirements.txt
```

2. **Install Ollama:**
```bash
# macOS
brew install ollama

# Linux
curl https://ollama.ai/install.sh | sh
```

3. **Pull required model:**
```bash
ollama pull llama3.2:3b
```

## Usage

### Web Interface (Recommended)

Start the web server:
```bash
# From project root
python chat_agents/run_server.py

# Or with auto-reload for development
python chat_agents/run_server.py --reload
```

Then open your browser to:
- **Web Interface**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

The web interface provides:
- Real-time chat with WebSocket connection
- Scholarship selection dropdown
- Beautiful, responsive UI
- Example queries to get started
- Conversation history within session

### Command Line Interface

Run the example script:
```bash
python chat_agents/example_chat.py
```

### Programmatic Usage

```python
from pathlib import Path
from agents.orchestrator import OrchestratorAgent

# Initialize orchestrator
orchestrator = OrchestratorAgent(
    outputs_dir=Path("../outputs"),
    model="llama3.2:3b"
)

# Ask questions
response = orchestrator.chat(
    "How many applicants are there?",
    scholarship="Delaney_Wings"
)
print(response)

# Continue conversation
response = orchestrator.chat(
    "Show me the top 5",
    scholarship="Delaney_Wings"
)
print(response)

# Reset conversation history
orchestrator.reset_history()
```

### Using Individual Agents

```python
from agents.results_agent import ResultsRetrievalAgent
from agents.explanation_agent import ScoreExplanationAgent
from agents.file_agent import FileRetrievalAgent

# Results agent
results_agent = ResultsRetrievalAgent()
response = results_agent.query("Show me the top 10 applicants")

# Explanation agent
explanation_agent = ScoreExplanationAgent()
response = explanation_agent.query("Explain the score for WAI 127830")

# File agent
file_agent = FileRetrievalAgent()
response = file_agent.query("List attachments for WAI 127830")
```

## Data Structure

The agents expect data in the following structure:

```
outputs/
└── {scholarship}/              # e.g., Delaney_Wings
    ├── summary.csv            # Summary of all applicants
    └── {WAI}/                 # e.g., 127830
        ├── application_data.json
        ├── application_analysis.json
        ├── recommendation_analysis.json
        ├── academic_analysis.json
        ├── essay_analysis.json
        └── attachments/
            ├── {WAI}_19_1.txt  # Recommendation 1
            ├── {WAI}_19_2.txt  # Recommendation 2
            ├── {WAI}_19_3.txt  # Resume
            ├── {WAI}_1_4.txt   # Essay 1
            ├── {WAI}_1_5.txt   # Essay 2
            └── _processing_summary.json
```

## Configuration

### Model Selection

Change the LLM model by passing a different model name:

```python
orchestrator = OrchestratorAgent(
    model="llama3:latest"  # or "gpt-4", "gpt-3.5-turbo", etc.
)
```

### Outputs Directory

Specify a different outputs directory:

```python
orchestrator = OrchestratorAgent(
    outputs_dir=Path("/path/to/outputs")
)
```

## Example Queries

### General Statistics
- "How many applicants are there in Delaney_Wings?"
- "What's the average final score?"
- "Show me statistics for Delaney_Wings"

### Rankings
- "Who are the top 10 applicants?"
- "Show me the top 5 by essay score"
- "List the highest-ranked applicants"

### Specific Applicants
- "Tell me about WAI 127830"
- "What's John Smith's score?"
- "Search for applicants named Maria"

### Score Explanations
- "Why did WAI 127830 get their application score?"
- "Explain the recommendation score for applicant 112222"
- "What validation errors does WAI 127830 have?"
- "Break down the scores for WAI 127830"

### File Access
- "List attachments for WAI 127830"
- "Where is the resume for applicant 112222?"
- "Show me the processing summary for WAI 127830"
- "What files are available for WAI 127830?"

## API Endpoints

The FastAPI server provides the following endpoints:

### REST API

**POST /api/chat/message**
- Send a chat message and get response
- Request body: `{"message": "...", "scholarship": "...", "session_id": "..."}`
- Response: `{"response": "...", "session_id": "...", "scholarship": "..."}`

**POST /api/session/create**
- Create a new chat session
- Response: `{"session_id": "...", "created": true}`

**DELETE /api/session/{session_id}**
- Delete a chat session

**POST /api/session/{session_id}/reset**
- Reset conversation history for a session

**GET /api/files/{scholarship}/{wai}/{filename}**
- Download attachment files
- Example: `/api/files/Delaney_Wings/127830/127830_19_1.txt`

**GET /api/scholarships**
- List available scholarships
- Response: `{"scholarships": ["Delaney_Wings", "Evans_Wings"]}`

**GET /health**
- Health check endpoint
- Response: `{"status": "healthy", "sessions": 0, ...}`

### WebSocket

**WS /ws/chat/{session_id}**
- Real-time chat connection
- Send: `{"message": "...", "scholarship": "..."}`
- Receive: `{"type": "response", "response": "...", "scholarship": "..."}`

### Interactive API Documentation

Visit http://localhost:8000/docs for interactive Swagger UI documentation where you can test all endpoints.

## Troubleshooting

### "Model not found" error
```bash
ollama pull llama3.2:3b
```

### "Import langchain" errors
```bash
pip install langchain langchain-community
```

### "No data found" errors
- Ensure outputs directory path is correct
- Verify summary.csv exists
- Check that analysis JSON files are present

## Contributing

This system was built with Bob (AI coding assistant) and follows best practices for:
- Modular agent design
- Clear separation of concerns
- Comprehensive error handling
- Detailed logging

## License

MIT License - See LICENSE file for details

## Author

Pat G Cappelaere, IBM Federal Consulting
Created: 2025-12-07

---

Made with Bob 🤖
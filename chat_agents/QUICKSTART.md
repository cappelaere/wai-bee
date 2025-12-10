# Quick Start Guide

Get the Scholarship Chat Agent system up and running in 5 minutes!

## Prerequisites

- Python 3.8 or higher
- Ollama installed (for local LLM)

## Step 1: Install Dependencies

```bash
# From project root
pip install -r requirements.txt
```

This installs:
- LangChain for agent framework
- FastAPI for web server
- Ollama client for LLM
- All other dependencies

## Step 2: Install and Start Ollama

### macOS
```bash
brew install ollama
ollama serve
```

### Linux
```bash
curl https://ollama.ai/install.sh | sh
ollama serve
```

### Pull the Model
In a new terminal:
```bash
ollama pull llama3.2:3b
```

## Step 3: Start the Web Server

```bash
# From project root
python chat_agents/run_server.py
```

You should see:
```
╔══════════════════════════════════════════════════════════════╗
║         Scholarship Chat Agent Server                        ║
╚══════════════════════════════════════════════════════════════╝

Starting server...
  Host: 0.0.0.0
  Port: 8000
  Reload: False

Web Interface: http://localhost:8000
API Docs: http://localhost:8000/docs
Health Check: http://localhost:8000/health
```

## Step 4: Open the Web Interface

Open your browser to: **http://localhost:8000**

You'll see a beautiful chat interface with:
- Scholarship selector dropdown
- Real-time chat with WebSocket
- Example queries to get started
- Conversation history

## Step 5: Try Some Queries

Click on the example queries or type your own:

### General Queries
- "How many applicants are there?"
- "Show me the top 10 applicants"
- "What's the average final score?"

### Specific Applicants
- "Tell me about WAI 127830"
- "Search for applicants named John"

### Score Explanations
- "Why did WAI 127830 get their application score?"
- "Explain the recommendation score for applicant 112222"

### File Access
- "List attachments for WAI 127830"
- "Where is the resume for applicant 112222?"

## Alternative: Command Line Interface

If you prefer CLI:

```bash
python chat_agents/example_chat.py
```

This provides an interactive command-line chat interface.

## Troubleshooting

### "Model not found" error
```bash
ollama pull llama3.2:3b
```

### "Connection refused" to Ollama
Make sure Ollama is running:
```bash
ollama serve
```

### "No data found" errors
Ensure you have processed scholarship data in the `outputs/` directory:
```bash
python examples/run_workflow.py
```

### Import errors
Make sure all dependencies are installed:
```bash
pip install -r requirements.txt
```

## What's Next?

### Explore the API
Visit http://localhost:8000/docs for interactive API documentation.

### Use Different Models
Edit `chat_agents/api/main.py` and change `DEFAULT_MODEL`:
```python
DEFAULT_MODEL = "llama3:latest"  # or "gpt-4", etc.
```

### Development Mode
Run with auto-reload for development:
```bash
python chat_agents/run_server.py --reload
```

### Production Deployment
See `chat_agents/README.md` for production deployment options.

## Architecture Overview

```
User Browser
    ↓
FastAPI Server (port 8000)
    ↓
Orchestrator Agent
    ↓
┌─────────────┬──────────────┬─────────────┐
│   Results   │ Explanation  │    File     │
│    Agent    │    Agent     │   Agent     │
└─────────────┴──────────────┴─────────────┘
    ↓
Data Tools (CSV, JSON, File Access)
    ↓
outputs/{scholarship}/{WAI}/
```

## Support

For issues or questions:
1. Check the main README: `chat_agents/README.md`
2. Review the troubleshooting section above
3. Check server logs for error messages

---

Made with Bob 🤖
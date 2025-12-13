# Agent Modes Documentation

## Overview

The scholarship chat system now supports two agent architectures that you can switch between using environment variables:

1. **Single-Agent Mode** (default): Uses a single unified agent for all tasks
2. **Multi-Agent Mode**: Uses orchestrator pattern with specialized agents

## Architecture

### Multi-Agent Mode (`AGENT_MODE=multi`)

```
┌─────────────────────────────────────┐
│     Orchestrator Agent              │
│  (Routes requests to specialists)   │
└──────────┬──────────────────────────┘
           │
           ├──────────────┬─────────────────┐
           │              │                 │
           ▼              ▼                 ▼
    ┌───────────┐   ┌──────────┐    ┌──────────┐
    │Scholarship│   │  Review  │    │  Future  │
    │  Agent    │   │  Agent   │    │  Agents  │
    └───────────┘   └──────────┘    └──────────┘
```

**Benefits:**
- Specialized agents for different tasks
- Better separation of concerns
- Can use different models for routing vs. execution
- Easier to add new specialized agents

**Files:**
- `bee_agents/chat_agents.py` - Multi-agent orchestration logic
- Uses `MultiAgentOrchestrator` class

### Single-Agent Mode (`AGENT_MODE=single`)

```
┌─────────────────────────────────────┐
│     Unified Agent                   │
│  (Handles all tasks directly)       │
│  - Scholarship queries              │
│  - Application analysis             │
│  - Statistics & reports             │
└─────────────────────────────────────┘
```

**Benefits:**
- Simpler architecture
- Lower latency (no routing overhead)
- Easier to debug
- Better for resource-constrained environments

**Files:**
- `bee_agents/chat_agents_single.py` - Single agent implementation
- Uses `SingleAgentHandler` class

## Configuration

### Environment Variables

| Variable | Values | Default | Description |
|----------|--------|---------|-------------|
| `AGENT_MODE` | `multi`, `single` | `single` | Agent architecture mode |
| `CHAT_MODEL` | Model string | `anthropic:claude-sonnet-4-20250514` | Main model for responses |
| `ORCHESTRATOR_MODEL` | Model string | Same as `CHAT_MODEL` | Model for routing (multi-agent only) |

### Supported Models

- **Anthropic**: `anthropic:claude-sonnet-4-20250514`
- **Ollama**: `ollama/llama3.2:3b`, `ollama/llama3:8b`, `ollama/qwen2.5:7b`
- **OpenAI**: `openai:gpt-4`, `openai:gpt-3.5-turbo`

## Usage Examples

### Single-Agent Mode (Default)

```bash
# Default configuration
python -m bee_agents.chat_api --port 8100

# With specific models
CHAT_MODEL="anthropic:claude-sonnet-4-20250514" python -m bee_agents.chat_api

# Single agent with local Ollama
CHAT_MODEL="ollama/llama3.2:3b" python -m bee_agents.chat_api
```

### Multi-Agent Mode

```bash
# Multi-agent with Anthropic
AGENT_MODE=multi \
CHAT_MODEL="anthropic:claude-sonnet-4-20250514" \
python -m bee_agents.chat_api

# Fast orchestrator, quality responses
AGENT_MODE=multi \
ORCHESTRATOR_MODEL="ollama/llama3.2:1b" \
CHAT_MODEL="anthropic:claude-sonnet-4-20250514" \
python -m bee_agents.chat_api
```

### Docker Deployment

Update your `docker-compose.yml` or `.env` file:

```yaml
environment:
  - AGENT_MODE=single  # or multi
  - CHAT_MODEL=anthropic:claude-sonnet-4-20250514
  - ORCHESTRATOR_MODEL=ollama/llama3.2:1b  # only for multi-agent
```

## Health Check

The `/health` endpoint now returns agent mode information:

```bash
curl http://localhost:8100/health
```

**Multi-Agent Response:**
```json
{
  "status": "healthy",
  "agent_mode": "multi",
  "orchestrator_initialized": true,
  "agents": {
    "scholarship": true,
    "review": false
  },
  "chat_model": "anthropic:claude-sonnet-4-20250514",
  "orchestrator_model": "anthropic:claude-sonnet-4-20250514"
}
```

**Single-Agent Response:**
```json
{
  "status": "healthy",
  "agent_mode": "single",
  "agent_initialized": true,
  "chat_model": "anthropic:claude-sonnet-4-20250514"
}
```

## When to Use Each Mode

### Use Multi-Agent Mode When:
- You need specialized behavior for different tasks
- You want to optimize costs (fast routing, quality responses)
- You're building a complex system with many capabilities
- You plan to add more specialized agents

### Use Single-Agent Mode When:
- You want simplicity and easier debugging
- You need lower latency
- You have resource constraints
- Your use case doesn't require specialization

## Implementation Details

### Code Organization

```
bee_agents/
├── chat_api.py              # FastAPI endpoints and WebSocket handling
├── chat_agents.py           # Multi-agent orchestration
├── chat_agents_single.py    # Single-agent implementation
├── auth.py                  # Authentication
├── middleware.py            # Access control
└── logging_config.py        # Logging setup
```

### Key Classes

**MultiAgentOrchestrator** (`chat_agents.py`):
- `initialize()` - Sets up orchestrator and specialized agents
- `get_agent()` - Returns the orchestrator agent
- `get_status()` - Returns system status

**SingleAgentHandler** (`chat_agents_single.py`):
- `initialize()` - Sets up the unified agent
- `get_agent()` - Returns the unified agent
- `get_status()` - Returns system status

### Switching Modes

The system automatically selects the appropriate handler based on `AGENT_MODE`:

```python
if AGENT_MODE == "single":
    agent_handler = SingleAgentHandler(CHAT_MODEL)
else:
    agent_handler = MultiAgentOrchestrator(CHAT_MODEL, ORCHESTRATOR_MODEL)

await agent_handler.initialize()
agent = agent_handler.get_agent()
```

## Testing

Test both modes to ensure they work correctly:

```bash
# Test multi-agent mode
AGENT_MODE=multi python -m bee_agents.chat_api --port 8100

# Test single-agent mode
AGENT_MODE=single python -m bee_agents.chat_api --port 8101
```

## Migration Guide

If you're upgrading from the previous version:

1. **No changes required** - Multi-agent mode is the default
2. **To try single-agent mode** - Set `AGENT_MODE=single`
3. **Configuration is backward compatible** - Existing environment variables work as before

## Troubleshooting

### Agent Not Initialized Error
- Check that `AGENT_MODE` is set to either `multi` or `single`
- Verify model names are correct
- Check logs for initialization errors

### Performance Issues
- Try single-agent mode for lower latency
- Use faster models for orchestrator in multi-agent mode
- Check network connectivity to model providers

### Model Not Found
- Verify model name format: `provider:model-name`
- For Ollama, ensure the model is pulled: `ollama pull llama3.2:3b`
- Check API keys for cloud providers

## Future Enhancements

Potential additions to the agent system:
- Review agent implementation (multi-agent mode)
- Additional specialized agents (e.g., statistics, reporting)
- Dynamic agent selection based on query complexity
- Agent performance monitoring and metrics
- A/B testing between modes

## Support

For issues or questions:
- Check logs in the console output
- Review the `/health` endpoint
- Consult the main README.md for general setup
- Check BeeAI framework documentation
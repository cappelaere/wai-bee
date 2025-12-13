# Agent Mode Quick Start Guide

## TL;DR

Switch between multi-agent and single-agent modes using the `AGENT_MODE` environment variable.

## Quick Commands

### Single-Agent Mode (Default)
```bash
python -m bee_agents.chat_api --port 8100
```

### Multi-Agent Mode
```bash
AGENT_MODE=multi python -m bee_agents.chat_api --port 8100
```

## Environment Variables

```bash
# Required
export AGENT_MODE=single          # or "multi" (default: single)
export CHAT_MODEL=anthropic:claude-sonnet-4-20250514

# Optional (multi-agent only)
export ORCHESTRATOR_MODEL=ollama/llama3.2:1b
```

## File Structure

```
bee_agents/
├── chat_api.py              # Main API (refactored to use handlers)
├── chat_agents.py           # Multi-agent orchestration
└── chat_agents_single.py    # Single-agent implementation

docs/
├── AGENT_MODES.md           # Full documentation
└── AGENT_MODE_QUICK_START.md # This file
```

## Key Differences

| Feature | Multi-Agent | Single-Agent |
|---------|-------------|--------------|
| Architecture | Orchestrator + Specialists | Unified Agent |
| Latency | Higher (routing overhead) | Lower |
| Complexity | More complex | Simpler |
| Debugging | Harder | Easier |
| Extensibility | Easy to add agents | Requires modification |
| Cost Optimization | Can use different models | Single model |

## Testing

```bash
# Check health endpoint
curl http://localhost:8100/health

# Expected response includes:
# - "agent_mode": "multi" or "single"
# - Agent initialization status
```

## Common Use Cases

**Use Multi-Agent When:**
- Building complex systems
- Need specialized behavior
- Want cost optimization (fast routing + quality responses)

**Use Single-Agent When:**
- Need simplicity
- Want lower latency
- Have resource constraints
- Debugging issues

## See Also

- [AGENT_MODES.MD](./AGENT_MODES.MD) - Full documentation
- [chat_agents.py](../bee_agents/chat_agents.py) - Multi-agent implementation
- [chat_agents_single.py](../bee_agents/chat_agents_single.py) - Single-agent implementation
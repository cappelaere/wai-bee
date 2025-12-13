# Ollama Setup Guide for Unix Systems

Complete guide to install Ollama, download models, and integrate with the WAI Scholarship system.

## Table of Contents
- [Installation](#installation)
- [Model Selection](#model-selection)
- [Downloading Models](#downloading-models)
- [Testing Models](#testing-models)
- [Integration with WAI System](#integration-with-wai-system)
- [Performance Comparison](#performance-comparison)
- [Troubleshooting](#troubleshooting)

---

## Installation

### Linux (Ubuntu/Debian/RHEL/CentOS)

**Method 1: Official Install Script (Recommended)**
```bash
# Download and install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Verify installation
ollama --version
```

**Method 2: Manual Installation**
```bash
# Download binary
curl -L https://ollama.com/download/ollama-linux-amd64 -o ollama
chmod +x ollama
sudo mv ollama /usr/local/bin/

# Create systemd service
sudo useradd -r -s /bin/false -m -d /usr/share/ollama ollama
sudo mkdir -p /usr/share/ollama

# Create service file
sudo tee /etc/systemd/system/ollama.service > /dev/null <<EOF
[Unit]
Description=Ollama Service
After=network-online.target

[Service]
ExecStart=/usr/local/bin/ollama serve
User=ollama
Group=ollama
Restart=always
RestartSec=3
Environment="OLLAMA_HOST=0.0.0.0:11434"

[Install]
WantedBy=default.target
EOF

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable ollama
sudo systemctl start ollama
```

### macOS

```bash
# Using Homebrew
brew install ollama

# Or download from https://ollama.com/download
```

### Start Ollama Service

```bash
# Start Ollama server (runs on http://localhost:11434)
ollama serve

# Or if installed as systemd service (Linux)
sudo systemctl start ollama
sudo systemctl status ollama
```

---

## Model Selection

### Recommended Models for WAI System

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| **llama3.2:1b** | 1.3 GB | ⚡⚡⚡ Very Fast | ⭐⭐ Basic | Orchestrator (routing) |
| **llama3.2:3b** | 2.0 GB | ⚡⚡ Fast | ⭐⭐⭐ Good | Chat responses |
| **llama3:8b** | 4.7 GB | ⚡ Moderate | ⭐⭐⭐⭐ Very Good | High-quality responses |
| **qwen2.5:7b** | 4.7 GB | ⚡ Moderate | ⭐⭐⭐⭐ Very Good | Alternative quality |
| **mistral:7b** | 4.1 GB | ⚡ Moderate | ⭐⭐⭐⭐ Very Good | Balanced performance |
| **phi3:3.8b** | 2.3 GB | ⚡⚡ Fast | ⭐⭐⭐ Good | Efficient alternative |

### Performance Estimates

**Response Time per LLM Call:**
- `llama3.2:1b`: 100-200ms (CPU) / 50-100ms (GPU)
- `llama3.2:3b`: 200-400ms (CPU) / 100-200ms (GPU)
- `llama3:8b`: 400-800ms (CPU) / 200-400ms (GPU)
- `qwen2.5:7b`: 300-600ms (CPU) / 150-300ms (GPU)

**Total Chat Response Time (4 LLM calls):**
- Fast setup (1b + 3b): **1-2 seconds**
- Balanced (3b + 3b): **1.5-2.5 seconds**
- Quality (3b + 8b): **2-4 seconds**

---

## Downloading Models

### Quick Start - Recommended Setup

```bash
# Fast orchestrator for routing decisions
ollama pull llama3.2:1b

# Good quality for chat responses
ollama pull llama3.2:3b

# Verify downloads
ollama list
```

### Full Model Suite for Testing

```bash
# Small models (fast)
ollama pull llama3.2:1b
ollama pull llama3.2:3b

# Medium models (balanced)
ollama pull phi3:3.8b
ollama pull mistral:7b

# Large models (quality)
ollama pull llama3:8b
ollama pull qwen2.5:7b

# Specialized models
ollama pull codellama:7b      # For code-related queries
ollama pull llama3.1:8b       # Latest Llama 3.1

# List all downloaded models
ollama list
```

### Model Management

```bash
# Remove a model
ollama rm llama3:8b

# Show model info
ollama show llama3.2:3b

# Update a model
ollama pull llama3.2:3b
```

---

## Testing Models

### Interactive Testing

```bash
# Test a model interactively
ollama run llama3.2:3b

# Example prompts:
# > What is a scholarship?
# > Explain the difference between merit and need-based scholarships.
# > /bye (to exit)
```

### Command-line Testing

```bash
# Single query test
ollama run llama3.2:3b "What are the key components of a scholarship application?"

# Test response time
time ollama run llama3.2:1b "Hello, how are you?"
```

### API Testing

```bash
# Test Ollama API
curl http://localhost:11434/api/generate -d '{
  "model": "llama3.2:3b",
  "prompt": "What is a scholarship?",
  "stream": false
}'

# Check available models
curl http://localhost:11434/api/tags
```

### Python Testing Script

Create `test_ollama_models.py`:

```python
#!/usr/bin/env python3
"""Test Ollama models for response time and quality."""

import time
import requests

OLLAMA_URL = "http://localhost:11434"
TEST_PROMPT = "Explain what a scholarship is in 2 sentences."

def test_model(model_name):
    """Test a single model."""
    print(f"\nTesting {model_name}...")
    
    start = time.time()
    response = requests.post(
        f"{OLLAMA_URL}/api/generate",
        json={
            "model": model_name,
            "prompt": TEST_PROMPT,
            "stream": False
        }
    )
    elapsed = time.time() - start
    
    if response.status_code == 200:
        result = response.json()
        print(f"  Time: {elapsed:.2f}s")
        print(f"  Response: {result['response'][:100]}...")
        return elapsed
    else:
        print(f"  Error: {response.status_code}")
        return None

# Test models
models = [
    "llama3.2:1b",
    "llama3.2:3b",
    "llama3:8b",
    "qwen2.5:7b"
]

print("Ollama Model Performance Test")
print("=" * 50)

for model in models:
    test_model(model)
```

Run with:
```bash
python test_ollama_models.py
```

---

## Integration with WAI System

### Configuration

Edit `.env` file:

```bash
# Fast Setup (Recommended for Development)
CHAT_MODEL="ollama/llama3.2:3b"
ORCHESTRATOR_MODEL="ollama/llama3.2:1b"

# Balanced Setup
CHAT_MODEL="ollama/llama3:8b"
ORCHESTRATOR_MODEL="ollama/llama3.2:3b"

# Quality Setup
CHAT_MODEL="ollama/qwen2.5:7b"
ORCHESTRATOR_MODEL="ollama/llama3.2:3b"

# Hybrid Setup (Fast routing + Cloud quality)
ORCHESTRATOR_MODEL="ollama/llama3.2:1b"
CHAT_MODEL="anthropic:claude-sonnet-4-20250514"
```

### Docker Compose Integration

Ollama is included in `docker-compose.yml` and will start automatically:

```bash
# Start all services including Ollama
docker-compose up -d

# Check Ollama status
docker-compose ps ollama
docker-compose logs ollama

# Pull models in Ollama container
docker-compose exec ollama ollama pull llama3.2:1b
docker-compose exec ollama ollama pull llama3.2:3b
```

### Local Development

```bash
# Make sure Ollama is running
sudo systemctl status ollama

# Or start manually
ollama serve &

# Run chat in development mode
make dev-chat

# Or with specific model
CHAT_MODEL="ollama/llama3.2:3b" make dev-chat
```

### Verify Integration

```bash
# Check health endpoint
curl http://localhost:8100/health | jq

# Should show:
# {
#   "status": "healthy",
#   "chat_model": "ollama/llama3.2:3b",
#   "orchestrator_model": "ollama/llama3.2:1b"
# }
```

---

## Performance Comparison

### Response Time Comparison

| Setup | Orchestrator | Chat Model | Total Time | Cost |
|-------|-------------|------------|------------|------|
| **Current (Claude)** | Claude Sonnet | Claude Sonnet | 4-6s | $$$$ |
| **Fast Ollama** | llama3.2:1b | llama3.2:3b | 1-2s | Free |
| **Balanced Ollama** | llama3.2:3b | llama3:8b | 2-3s | Free |
| **Hybrid** | llama3.2:1b | Claude Sonnet | 2-3s | $$$ |

### Quality vs Speed Trade-off

```
Quality ⭐⭐⭐⭐⭐ Claude Sonnet (4-6s, $$$)
        ⭐⭐⭐⭐   llama3:8b / qwen2.5:7b (2-4s, Free)
        ⭐⭐⭐     llama3.2:3b (1-2s, Free)
        ⭐⭐       llama3.2:1b (0.5-1s, Free)
```

---

## Troubleshooting

### Ollama Not Starting

```bash
# Check if port 11434 is in use
sudo lsof -i :11434

# Check Ollama logs
sudo journalctl -u ollama -f

# Restart Ollama
sudo systemctl restart ollama
```

### Model Download Issues

```bash
# Check disk space
df -h

# Check Ollama data directory
ls -lh ~/.ollama/models/

# Clear cache and re-download
rm -rf ~/.ollama/models/
ollama pull llama3.2:3b
```

### Connection Issues

```bash
# Test Ollama API
curl http://localhost:11434/api/tags

# Check firewall
sudo ufw status
sudo ufw allow 11434/tcp

# Check Ollama environment
env | grep OLLAMA
```

### Performance Issues

```bash
# Check CPU/Memory usage
htop

# Check GPU availability (if using GPU)
nvidia-smi

# Reduce concurrent requests
# Edit .env:
MAX_WORKERS=1
```

### Docker Integration Issues

```bash
# Check Ollama container
docker-compose ps ollama
docker-compose logs ollama

# Restart Ollama container
docker-compose restart ollama

# Pull models in container
docker-compose exec ollama ollama pull llama3.2:3b
```

---

## Best Practices

1. **Start Small**: Begin with `llama3.2:1b` and `llama3.2:3b`
2. **Test Performance**: Use the test script to compare models
3. **Monitor Resources**: Watch CPU/Memory usage during operation
4. **Use GPU**: If available, Ollama will automatically use GPU for 5-10x speedup
5. **Hybrid Approach**: Use Ollama for routing, Claude for complex queries
6. **Keep Updated**: Regularly update models with `ollama pull`

---

## Quick Reference

```bash
# Installation
curl -fsSL https://ollama.com/install.sh | sh

# Start service
sudo systemctl start ollama

# Download recommended models
ollama pull llama3.2:1b
ollama pull llama3.2:3b

# Configure WAI system
# Edit .env:
CHAT_MODEL="ollama/llama3.2:3b"
ORCHESTRATOR_MODEL="ollama/llama3.2:1b"

# Deploy
docker-compose up -d

# Test
curl http://localhost:8100/health
```

---

**Made with Bob**
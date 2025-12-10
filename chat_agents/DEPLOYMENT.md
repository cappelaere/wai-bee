# Deployment Guide

Guide for deploying the Scholarship Chat Agent system to production.

## Table of Contents

1. [Docker Deployment](#docker-deployment)
2. [Security Considerations](#security-considerations)
3. [Environment Configuration](#environment-configuration)
4. [Production Best Practices](#production-best-practices)
5. [Monitoring and Logging](#monitoring-and-logging)

## Docker Deployment

### Dockerfile

Create `Dockerfile` in the project root:

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Ollama
RUN curl https://ollama.ai/install.sh | sh

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Start script
COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh

ENTRYPOINT ["/docker-entrypoint.sh"]
```

### Docker Entrypoint Script

Create `docker-entrypoint.sh`:

```bash
#!/bin/bash
set -e

# Start Ollama in background
ollama serve &

# Wait for Ollama to be ready
sleep 5

# Pull model if not exists
ollama pull llama3.2:3b

# Start FastAPI server
exec python chat_agents/run_server.py --host 0.0.0.0 --port 8000
```

### Docker Compose

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  chat-agent:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./outputs:/app/outputs:ro
      - ollama-data:/root/.ollama
    environment:
      - OLLAMA_HOST=http://localhost:11434
      - LOG_LEVEL=info
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  ollama-data:
```

### Build and Run

```bash
# Build image
docker-compose build

# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Security Considerations

### 1. Authentication

Add JWT authentication to `chat_agents/api/main.py`:

```python
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from datetime import datetime, timedelta

security = HTTPBearer()
SECRET_KEY = "your-secret-key-here"  # Use environment variable
ALGORITHM = "HS256"

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Add to protected endpoints
@app.post("/api/chat/message", dependencies=[Depends(verify_token)])
async def chat_message(request: ChatMessage):
    # ... existing code
```

### 2. Rate Limiting

Install and configure rate limiting:

```bash
pip install slowapi
```

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/chat/message")
@limiter.limit("10/minute")
async def chat_message(request: Request, chat_request: ChatMessage):
    # ... existing code
```

### 3. CORS Configuration

Update CORS for production:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://yourdomain.com",
        "https://www.yourdomain.com"
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)
```

### 4. HTTPS/WSS

Use a reverse proxy (nginx) with SSL:

```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws/ {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

### 5. Input Validation

Add input validation and sanitization:

```python
from pydantic import BaseModel, validator, Field

class ChatMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    scholarship: str = Field(..., regex="^[a-zA-Z_]+$")
    session_id: Optional[str] = Field(None, regex="^[a-f0-9-]{36}$")

    @validator('message')
    def sanitize_message(cls, v):
        # Remove potentially harmful characters
        return v.strip()
```

## Environment Configuration

Create `.env` file:

```bash
# Server Configuration
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=info

# LLM Configuration
OLLAMA_HOST=http://localhost:11434
DEFAULT_MODEL=llama3.2:3b

# Security
SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# Rate Limiting
RATE_LIMIT_PER_MINUTE=10

# CORS
ALLOWED_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Data
OUTPUTS_DIR=/app/outputs
```

Load in `api/main.py`:

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"
    ollama_host: str = "http://localhost:11434"
    default_model: str = "llama3.2:3b"
    secret_key: str
    outputs_dir: Path = Path("outputs")
    
    class Config:
        env_file = ".env"

settings = Settings()
```

## Production Best Practices

### 1. Use Production ASGI Server

Replace uvicorn with gunicorn + uvicorn workers:

```bash
pip install gunicorn
```

```bash
gunicorn chat_agents.api.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile -
```

### 2. Session Management

Use Redis for session storage:

```bash
pip install redis aioredis
```

```python
import aioredis
from typing import Optional

redis = aioredis.from_url("redis://localhost")

async def get_session(session_id: str) -> Optional[OrchestratorAgent]:
    data = await redis.get(f"session:{session_id}")
    if data:
        return pickle.loads(data)
    return None

async def save_session(session_id: str, agent: OrchestratorAgent):
    await redis.setex(
        f"session:{session_id}",
        3600,  # 1 hour TTL
        pickle.dumps(agent)
    )
```

### 3. Graceful Shutdown

Handle shutdown signals:

```python
import signal
import asyncio

def handle_shutdown(signum, frame):
    logger.info("Shutting down gracefully...")
    # Close WebSocket connections
    for session_id, ws in active_connections.items():
        asyncio.create_task(ws.close())
    # Save sessions
    # Clean up resources
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)
```

### 4. Health Checks

Enhanced health check:

```python
@app.get("/health")
async def health_check():
    # Check Ollama connection
    try:
        # Test Ollama
        ollama_healthy = True
    except:
        ollama_healthy = False
    
    # Check data directory
    data_healthy = OUTPUTS_DIR.exists()
    
    status = "healthy" if (ollama_healthy and data_healthy) else "unhealthy"
    
    return {
        "status": status,
        "ollama": ollama_healthy,
        "data": data_healthy,
        "sessions": len(sessions),
        "timestamp": datetime.utcnow().isoformat()
    }
```

## Monitoring and Logging

### 1. Structured Logging

```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
        }
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_data)

handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
```

### 2. Metrics Collection

Use Prometheus for metrics:

```bash
pip install prometheus-client
```

```python
from prometheus_client import Counter, Histogram, generate_latest

# Metrics
chat_requests = Counter('chat_requests_total', 'Total chat requests')
chat_duration = Histogram('chat_duration_seconds', 'Chat request duration')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

### 3. Error Tracking

Integrate Sentry:

```bash
pip install sentry-sdk
```

```python
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

sentry_sdk.init(
    dsn="your-sentry-dsn",
    integrations=[FastApiIntegration()],
    traces_sample_rate=1.0,
)
```

## Deployment Checklist

- [ ] Environment variables configured
- [ ] SSL certificates installed
- [ ] Authentication enabled
- [ ] Rate limiting configured
- [ ] CORS properly set
- [ ] Logging configured
- [ ] Health checks working
- [ ] Monitoring set up
- [ ] Backup strategy in place
- [ ] Documentation updated
- [ ] Load testing completed
- [ ] Security audit performed

---

Made with Bob 🤖
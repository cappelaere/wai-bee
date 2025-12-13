# Docker Deployment Guide for WAI Scholarship Analysis System

This guide explains how to build and deploy the WAI Scholarship Analysis API and Chat Frontend using Docker.

## Prerequisites

- Docker Engine 20.10+ installed
- Docker Compose 2.0+ installed (optional, for multi-service deployment)
- At least 8GB of available disk space (for dependencies and models)
- 4GB+ RAM recommended

## Quick Start

### 1. Build the Docker Images

**Build API server:**
```bash
docker build -f Dockerfile-api -t wai-scholarship-api:latest .
```

**Build Chat frontend:**
```bash
docker build -f Dockerfile-chat -t wai-chat-frontend:latest .
```

**Or build all at once:**
```bash
make build-all
```

This will create multi-stage Docker images with all dependencies installed.

### 2. Run a Single Container

**For Delaney Wings scholarship:**
```bash
docker run -d \
  --name wai-delaney-api \
  -p 8000:8000 \
  -e SCHOLARSHIP=Delaney_Wings \
  -v $(pwd)/data/Delaney_Wings:/app/data/Delaney_Wings:ro \
  -v $(pwd)/outputs:/app/outputs \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/config:/app/config:ro \
  --env-file .env \
  wai-scholarship-api:latest
```

**For Evans Wings scholarship:**
```bash
docker run -d \
  --name wai-evans-api \
  -p 8001:8000 \
  -e SCHOLARSHIP=Evans_Wings \
  -v $(pwd)/data/Evans_Wings:/app/data/Evans_Wings:ro \
  -v $(pwd)/outputs:/app/outputs \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/config:/app/config:ro \
  --env-file .env \
  wai-scholarship-api:latest
```

### 3. Run Chat Frontend

```bash
docker run -d \
  --name wai-chat-frontend \
  -p 8100:8100 \
  -v $(pwd)/outputs:/app/outputs:ro \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/config:/app/config:ro \
  --env-file .env \
  wai-chat-frontend:latest
```

### 4. Using Docker Compose (Recommended)

Deploy both scholarship APIs simultaneously:

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all services
docker-compose down
```

**Note:** The docker-compose.yml currently includes only the API services. To add the chat frontend, you can run it separately using the command above or add it to your docker-compose.yml.

## Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# API Configuration
API_SERVER_URL=http://localhost:8000

# Authentication
ADMIN_PASSWORD=your_admin_password
USER_PASSWORD=your_user_password
DELANEY_PASSWORD=your_delaney_password
EVANS_PASSWORD=your_evans_password

# LLM Configuration
PRIMARY_MODEL=ollama/llama3.2:1b
FALLBACK_MODEL=ollama/llama3:latest
LARGE_MODEL=ollama/llama3.2:3b
MAX_RETRIES=3
LLM_TEMPERATURE=0.1
LLM_MAX_TOKENS=4000

# Optional: OpenAI/Anthropic
# OPENAI_API_KEY=your_key_here
# ANTHROPIC_API_KEY=your_key_here
# CHAT_MODEL=anthropic:claude-sonnet-4-20250514

# Processing Configuration
MAX_APPLICATIONS=None
SKIP_PROCESSED=true
OVERWRITE_EXISTING=false

# Logging
LOG_LEVEL=INFO
```

### Volume Mounts

The container uses the following volume mounts:

- **Data (read-only)**: `./data/{scholarship}:/app/data/{scholarship}:ro`
  - Contains scholarship application files
  - Mounted as read-only for security

- **Outputs**: `./outputs:/app/outputs`
  - Stores processed JSON results
  - Persisted across container restarts

- **Logs**: `./logs:/app/logs`
  - Application and access logs
  - Persisted for debugging

- **Config (read-only)**: `./config:/app/config:ro`
  - User configuration files
  - Mounted as read-only

## Service Access

Once running, access the services at:

### API Servers
- **Delaney Wings API**: http://localhost:8000
- **Evans Wings API**: http://localhost:8001 (if using docker-compose)

### Chat Frontend
- **Web Interface**: http://localhost:8200
- **API Documentation**: http://localhost:8200/docs
- **WebSocket**: ws://localhost:8200/ws/chat/{session_id}

### API Documentation

Interactive API documentation is available at:
- **Delaney API Swagger UI**: http://localhost:8000/docs
- **Evans API Swagger UI**: http://localhost:8001/docs
- **Chat API Swagger UI**: http://localhost:8200/docs
- **OpenAPI Schema**: http://localhost:8000/openapi.json

### Health Check

Check API health:
```bash
curl http://localhost:8000/health
```

Expected responses:

**API Server:**
```json
{
  "status": "healthy",
  "scholarship": "Delaney_Wings",
  "timestamp": "2025-12-10T19:56:00Z"
}
```

**Chat Frontend:**
```bash
curl http://localhost:8200/health
```
```json
{
  "status": "healthy",
  "sessions": 0,
  "outputs_dir": "/app/outputs",
  "model": "llama3.2:3b"
}
```

## Docker Commands

### View Logs

```bash
# All logs
docker logs wai-delaney-api

# Follow logs in real-time
docker logs -f wai-delaney-api

# Last 100 lines
docker logs --tail 100 wai-delaney-api
```

### Container Management

```bash
# Stop container
docker stop wai-delaney-api

# Start container
docker start wai-delaney-api

# Restart container
docker restart wai-delaney-api

# Remove container
docker rm wai-delaney-api

# Remove container and volumes
docker rm -v wai-delaney-api

# Chat frontend logs
docker logs -f wai-chat-frontend
```

### Inspect Container

```bash
# View container details
docker inspect wai-delaney-api

# View resource usage
docker stats wai-delaney-api

# Execute command in container
docker exec -it wai-delaney-api bash

# Execute in chat frontend
docker exec -it wai-chat-frontend bash
```

### Build Chat Frontend

```bash
# Build chat frontend
make build-chat

# Or manually
docker build -f Dockerfile-chat -t wai-chat-frontend:latest .
```

### Run Chat Frontend

```bash
# Run chat frontend
make run-chat

# Or manually
docker run -d \
  --name wai-chat-frontend \
  -p 8200:8200 \
  -v $(pwd)/outputs:/app/outputs:ro \
  -v $(pwd)/logs:/app/logs \
  --env-file .env \
  wai-chat-frontend:latest
```

## Docker Compose Commands

### Service Management

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d delaney-api

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v

# Restart services
docker-compose restart

# View service status
docker-compose ps
```

### Logs

```bash
# View all logs
docker-compose logs

# Follow logs
docker-compose logs -f

# Logs for specific service
docker-compose logs -f delaney-api

# Last 100 lines
docker-compose logs --tail 100
```

### Scaling

```bash
# Scale a service (if needed)
docker-compose up -d --scale delaney-api=2
```

## Production Deployment

### Security Considerations

1. **Use secrets management** for sensitive environment variables
2. **Enable HTTPS** with a reverse proxy (nginx, traefik)
3. **Implement rate limiting** to prevent abuse
4. **Regular security updates** for base images
5. **Run as non-root user** (already configured in Dockerfile)

### Reverse Proxy Example (nginx)

```nginx
server {
    listen 80;
    server_name api.example.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Resource Limits

Add resource limits in docker-compose.yml:

```yaml
services:
  delaney-api:
    # ... other config ...
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

## Troubleshooting

### Container Won't Start

1. Check logs: `docker logs wai-delaney-api`
2. Verify environment variables in `.env`
3. Ensure data directories exist and have correct permissions
4. Check port availability: `netstat -tuln | grep 8000`

### Out of Memory

1. Increase Docker memory limit in Docker Desktop settings
2. Add memory limits to docker-compose.yml
3. Reduce `MAX_WORKERS` in environment variables

### Slow Performance

1. Check resource usage: `docker stats`
2. Ensure sufficient disk space
3. Consider using faster storage (SSD)
4. Optimize `MAX_APPLICATIONS` and parallel processing settings

### Permission Errors

```bash
# Fix output directory permissions
sudo chown -R 1000:1000 outputs logs

# Or run with current user
docker run --user $(id -u):$(id -g) ...
```

## Building for Different Architectures

### Build for ARM64 (Apple Silicon, ARM servers)

```bash
docker buildx build -f Dockerfile-api --platform linux/arm64 -t wai-scholarship-api:arm64 .
```

### Multi-architecture Build

```bash
docker buildx create --use
docker buildx build -f Dockerfile-api --platform linux/amd64,linux/arm64 -t wai-scholarship-api:latest --push .
```

## Maintenance

### Update Dependencies

1. Update `requirements.txt`
2. Rebuild image: `docker-compose build --no-cache`
3. Restart services: `docker-compose up -d`

### Backup Data

```bash
# Backup outputs
tar -czf outputs-backup-$(date +%Y%m%d).tar.gz outputs/

# Backup logs
tar -czf logs-backup-$(date +%Y%m%d).tar.gz logs/
```

### Clean Up

```bash
# Remove unused images
docker image prune -a

# Remove unused volumes
docker volume prune

# Remove everything unused
docker system prune -a --volumes
```

## Monitoring

### Health Checks

The container includes built-in health checks that run every 30 seconds:

```bash
# Check health status
docker inspect --format='{{.State.Health.Status}}' wai-delaney-api
```

### Prometheus Metrics (Optional)

Add prometheus metrics endpoint by installing `prometheus-fastapi-instrumentator`:

```python
from prometheus_fastapi_instrumentator import Instrumentator

Instrumentator().instrument(app).expose(app)
```

## Support

For issues or questions:
- Check logs: `docker-compose logs -f`
- Review API documentation: http://localhost:8000/docs
- Verify environment configuration in `.env`

## License

[Add your license information here]
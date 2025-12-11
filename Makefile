.PHONY: help build run stop clean logs shell test health deploy

# Load environment variables from .env file
include .env
export

# Default target
help:
	@echo "WAI Scholarship Analysis API - Docker Commands"
	@echo ""
	@echo "Available targets:"
	@echo "  build-api      - Build API Docker image"
	@echo "  build-chat     - Build Chat frontend Docker image"
	@echo "  build-all      - Build all Docker images"
	@echo "  run-api        - Run API container"
	@echo "  run-chat       - Run Chat frontend container"
	@echo "  deploy         - Deploy all services with docker-compose"
	@echo "  stop           - Stop all running containers"
	@echo "  restart        - Restart all services"
	@echo "  logs           - View logs from all services"
	@echo "  logs-api       - View API logs"
	@echo "  logs-chat      - View Chat logs"
	@echo "  logs-ollama    - View Ollama logs"
	@echo "  shell          - Open shell in API container"
	@echo "  health         - Check health of all services"
	@echo "  ollama-pull    - Pull recommended Ollama models"
	@echo "  ollama-list    - List downloaded Ollama models"
	@echo "  clean          - Remove containers and images"
	@echo "  clean-all      - Remove containers, images, and volumes"
	@echo "  test           - Run API tests"
	@echo "  backup         - Backup outputs and logs"
	@echo ""

# Build Docker image
build-api:
	@echo "Building API Docker image..."
	docker build -f Dockerfile-api -t wai-api:latest .

# Build chat frontend image
build-chat:
	@echo "Building Chat frontend Docker image..."
	docker build -f Dockerfile-chat -t wai-chat:latest .

# Build all images
build-all: build-api build-chat
	@echo "All images built successfully"

# Build without cache
build-no-cache:
	@echo "Building Docker image (no cache)..."
	docker build --no-cache -f Dockerfile-api -t wai-api:latest .

# Build chat without cache
build-chat-no-cache:
	@echo "Building Chat frontend Docker image (no cache)..."
	docker build --no-cache -f Dockerfile-chat -t wai-chat:latest .

# Run API container
run-api:
	@echo "Starting API server on port 8200..."
	docker run -d \
		--name wai-api \
		-p 8200:8200 \
		-v $$(pwd)/bee_agents:/app/bee_agents:ro \
		-v $$(pwd)/data:/app/data:ro \
		-v $$(pwd)/outputs:/app/outputs \
		-v $$(pwd)/logs:/app/logs \
		-v $$(pwd)/config:/app/config:ro \
		--env-file .env \
		wai-api:latest
	@echo "API running at http://$(HOST):8200"
	@echo "Documentation at http://$(HOST):8200/docs"

# Run Chat frontend container
run-chat:
	@echo "Starting Chat frontend on port 8100..."
	docker run -d \
		--name wai-chat\
		-p 8100:8100 \
		-v $$(pwd)/bee_agents:/app/bee_agents:ro \
		-v $$(pwd)/data:/app/data:ro \
		-v $$(pwd)/outputs:/app/outputs:ro \
		-v $$(pwd)/logs:/app/logs \
		-v $$(pwd)/config:/app/config:ro \
		--env-file .env \
		wai-chat:latest
	@echo "Chat frontend running at http://$(HOST):8100"
	@echo "Login at http://$(HOST):8100/login"

# Deploy with docker-compose
deploy:
	@echo "Deploying all services with docker-compose..."
	docker compose up -d
	@echo ""
	@echo "Services deployed:"
	@echo "  API Server:        http://$(HOST):8200/docs"
	@echo "  Chat Frontend:     http://$(HOST):8100/login"
	@echo "  Ollama:            http://$(HOST):11434"
	@echo ""
	@echo "View logs with: make logs"
	@echo "Pull Ollama models: make ollama-pull"

# Stop all containers
stop:
	@echo "Stopping all containers..."
	-docker stop wai-api wai-chat wai-ollama 2>/dev/null || true
	-docker compose down 2>/dev/null || true
	@echo "All containers stopped"

# Restart services
restart:
	@echo "Restarting services..."
	docker-compose restart
	@echo "Services restarted"

# View logs
logs:
	docker-compose logs -f

logs-api:
	docker logs -f wai-api

logs-chat:
	docker logs -f wai-chat

logs-ollama:
	docker logs -f wai-ollama

# Open shell in container
shell:
	docker exec -it wai-api bash

# Check health
health:
	@echo "Checking service health..."
	@echo ""
	@echo "API Server:"
	@curl -s http://$(HOST):8200/health | python -m json.tool || echo "  Service not responding"
	@echo ""
	@echo "Chat Frontend:"
	@curl -s http://$(HOST):8100/health | python -m json.tool || echo "  Service not responding"
	@echo ""
	@echo "Ollama:"
	@curl -s http://$(HOST):11434/api/tags | python -m json.tool || echo "  Service not responding"

# Ollama model management
ollama-pull:
	@echo "Pulling recommended Ollama models..."
	@echo "This may take several minutes depending on your connection..."
	@echo ""
	@echo "Pulling llama3.2:1b (fast orchestrator)..."
	docker-compose exec ollama ollama pull llama3.2:1b
	@echo ""
	@echo "Pulling llama3.2:3b (balanced chat)..."
	docker-compose exec ollama ollama pull llama3.2:3b
	@echo ""
	@echo "Models downloaded successfully!"
	@echo "Update .env to use: CHAT_MODEL=\"ollama/llama3.2:3b\""

ollama-list:
	@echo "Downloaded Ollama models:"
	@docker-compose exec ollama ollama list

ollama-pull-all:
	@echo "Pulling all recommended models (this will take a while)..."
	docker-compose exec ollama ollama pull llama3.2:1b
	docker-compose exec ollama ollama pull llama3.2:3b
	docker-compose exec ollama ollama pull llama3:8b
	docker-compose exec ollama ollama pull qwen2.5:7b
	@echo "All models downloaded!"

# Run tests
test:
	@echo "Running API tests..."
	docker exec wai-api python -m pytest tests/ -v

# Clean up containers and images
clean:
	@echo "Removing containers and images..."
	-docker stop wai-api wai-chat wai-ollama 2>/dev/null || true
	-docker rm wai-api wai-chat wai-ollama 2>/dev/null || true
	-docker compose down 2>/dev/null || true
	-docker rmi wai-api:latest wai-chat:latest 2>/dev/null || true
	@echo "Cleanup complete (Ollama data preserved in volume)"

# Clean everything including volumes
clean-all: clean
	@echo "Removing volumes..."
	-docker volume prune -f
	@echo "Full cleanup complete"

# Backup outputs and logs
backup:
	@echo "Creating backup..."
	@mkdir -p backups
	tar -czf backups/outputs-$$(date +%Y%m%d-%H%M%S).tar.gz outputs/
	tar -czf backups/logs-$$(date +%Y%m%d-%H%M%S).tar.gz logs/
	@echo "Backup created in backups/ directory"

# Show running containers
ps:
	@echo "Running containers:"
	@docker ps --filter "name=wai-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Show resource usage
stats:
	docker stats --no-stream wai-api wai-chat langfuse langfuse-db

# Pull latest base image
pull:
	docker pull python:3.11-slim

# Development mode with auto-reload (local, no Docker)
dev-api:
	@echo "Starting API in development mode with auto-reload..."
	@echo "Make sure you have activated the virtual environment first!"
	uvicorn bee_agents.api:app --host 0.0.0.0 --port 8200 --reload

# Development mode for chat frontend (local, no Docker)
dev-chat:
	@echo "Starting chat frontend in development mode with auto-reload..."
	@echo "Make sure you have activated the virtual environment first!"
	uvicorn bee_agents.chat_api:app --host 0.0.0.0 --port 8100 --reload

# Development mode - both services with auto-reload (local)
dev-all:
	@echo "Starting both API and Chat in development mode..."
	@echo "Make sure you have activated the virtual environment first!"
	@echo ""
	@echo "Starting API on port 8200..."
	@uvicorn bee_agents.api:app --host 0.0.0.0 --port 8200 --reload &
	@sleep 2
	@echo "Starting Chat on port 8100..."
	@uvicorn bee_agents.chat_api:app --host 0.0.0.0 --port 8100 --reload &
	@echo ""
	@echo "Services running:"
	@echo "  API:  http://$(HOST):8200/docs"
	@echo "  Chat: http://$(HOST):8100"
	@echo ""
	@echo "Press Ctrl+C to stop both services"
	@wait

# Development mode with Docker and auto-reload
dev-api-docker:
	@echo "Starting API in Docker development mode with auto-reload..."
	docker run -it --rm \
		--name wai-api-dev \
		-p 8200:8200 \
		-v $$(pwd)/bee_agents:/app/bee_agents \
		-v $$(pwd)/data:/app/data:ro \
		-v $$(pwd)/outputs:/app/outputs \
		-v $$(pwd)/logs:/app/logs \
		-v $$(pwd)/config:/app/config:ro \
		--env-file .env \
		--network wai-bee_wai-network \
		wai-api:latest \
		uvicorn bee_agents.api:app --host 0.0.0.0 --port 8200 --reload

# Development mode for chat with Docker and auto-reload
dev-chat-docker:
	@echo "Starting chat frontend in Docker development mode with auto-reload..."
	docker run -it --rm \
		--name wai-chat-dev \
		-p 8100:8100 \
		-v $$(pwd)/bee_agents:/app/bee_agents \
		-v $$(pwd)/data:/app/data:ro \
		-v $$(pwd)/outputs:/app/outputs:ro \
		-v $$(pwd)/logs:/app/logs \
		-v $$(pwd)/config:/app/config:ro \
		--env-file .env \
		--network wai-bee_wai-network \
		wai-chat:latest \
		uvicorn bee_agents.chat_api:app --host 0.0.0.0 --port 8100 --reload

# Quick rebuild and deploy
redeploy: build-all deploy
	@echo "Rebuild and deploy complete"
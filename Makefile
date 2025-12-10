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
	@echo "  logs-delaney   - View Delaney Wings logs"
	@echo "  logs-evans     - View Evans Wings logs"
	@echo "  shell          - Open shell in Delaney container"
	@echo "  health         - Check health of all services"
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
	@echo ""
	@echo "View logs with: make logs"

# Stop all containers
stop:
	@echo "Stopping all containers..."
	-docker stop wai-api wai-chat 2>/dev/null || true
	-docker-compose down 2>/dev/null || true
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

# Run tests
test:
	@echo "Running API tests..."
	docker exec wai-api python -m pytest tests/ -v

# Clean up containers and images
clean:
	@echo "Removing containers and images..."
	-docker stop wai-api wai-chat 2>/dev/null || true
	-docker rm wai-api wai-chat 2>/dev/null || true
	-docker-compose down 2>/dev/null || true
	-docker rmi wai-api:latest wai-chat:latest 2>/dev/null || true
	@echo "Cleanup complete"

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
	docker stats --no-stream wai-api wai-chat

# Pull latest base image
pull:
	docker pull python:3.11-slim

# Development mode with auto-reload
dev-api:
	@echo "Starting in development mode with auto-reload..."
	docker run -it --rm \
		--name wai-api-dev \
		-p 8000:8000 \
		-e SCHOLARSHIP=Delaney_Wings \
		-v $$(pwd):/app \
		-v $$(pwd)/data/Delaney_Wings:/app/data/Delaney_Wings:ro \
		-v $$(pwd)/outputs:/app/outputs \
		-v $$(pwd)/logs:/app/logs \
		--env-file .env \
		wai-api:latest \
		python -m bee_agents.run_api --reload

# Development mode for chat frontend
dev-chat:
	@echo "Starting chat frontend in development mode with auto-reload..."
	docker run -it --rm \
		--name wai-chat-dev \
		-p 8100:8100 \
		-v $$(pwd)/bee_agents:/app/bee_agents \
		-v $$(pwd)/data:/app/data:ro \
		-v $$(pwd)/outputs:/app/outputs:ro \
		-v $$(pwd)/logs:/app/logs \
		-v $$(pwd)/config:/app/config:ro \
		--env-file .env \
		wai-chat-frontend:latest \
		python -m bee_agents.chat_api --host 0.0.0.0 --port 8100

# Quick rebuild and deploy
redeploy: build-all deploy
	@echo "Rebuild and deploy complete"
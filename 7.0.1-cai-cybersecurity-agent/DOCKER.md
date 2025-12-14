# Docker Deployment Guide

## Overview

This guide covers running the CAI Cybersecurity Agent system using Docker and Docker Compose.

## Quick Start

### Option 1: Using Docker Compose (Recommended)

```bash
# 1. Create .env file with your API keys
cp .env.example .env
# Edit .env and add your DEEPSEEK_API_KEY

# 2. Start all services
docker-compose up -d

# 3. Check status
docker-compose ps

# 4. View logs
docker-compose logs -f

# 5. Register the cybersecurity agent
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"name": "cybersecurity-agent", "url": "http://cybersecurity:9003"}'

# 6. Stop services
docker-compose down
```

### Option 2: Build and Run Individually

**Cybersecurity Agent:**
```bash
cd cybersecurity-agent
docker build -t cai-cybersecurity-agent .
docker run -d \
  -p 9003:9003 \
  -e DEEPSEEK_API_KEY=your-key \
  --name cybersecurity-agent \
  cai-cybersecurity-agent
```

**Orchestrator Agent:**
```bash
cd orchestrator-agent
docker build -t cai-orchestrator .
docker run -d \
  -p 8000:8000 \
  -e DEEPSEEK_API_KEY=your-key \
  -v orchestrator_data:/data \
  --name orchestrator \
  cai-orchestrator
```

## Docker Compose Configuration

### Services

#### Orchestrator
- **Port**: 8000 (Registry API)
- **Volume**: `/data` (agent registry storage)
- **Health Check**: `/health` endpoint
- **Environment**: Model config, registry settings

#### Cybersecurity Agent
- **Port**: 9003 (A2A Protocol)
- **Health Check**: `/health` endpoint
- **Environment**: Model config, agent settings
- **Depends On**: Orchestrator service

### Volumes

- `orchestrator_data` - Persists agent registry across restarts

### Networks

- `cai_network` - Bridges orchestrator and cybersecurity agent

## Environment Variables

Create a `.env` file for docker-compose:

```bash
# Required
DEEPSEEK_API_KEY=your-deepseek-api-key

# Optional - defaults provided in docker-compose.yml
OPENAI_API_KEY=your-openai-api-key
DEEPSEEK_BASE_URL=https://api.deepseek.ai/v1/
DEEPSEEK_MODEL=deepseek-chat

# Orchestrator settings
ORCHESTRATOR_DEEPSEEK_TIMEOUT=60
ORCHESTRATOR_MAX_TOKENS=2000
ORCHESTRATOR_TEMPERATURE=0.7
ORCHESTRATOR_ENABLE_MEMORY=false

# Cybersecurity agent settings
CYBERSECURITY_AGENT_TIMEOUT=60
CYBERSECURITY_AGENT_MAX_TOKENS=600
CYBERSECURITY_AGENT_TEMPERATURE=0.2

# Session and debug
SESSION_ID=default-session
DEBUG=false
```

## Docker Compose Commands

```bash
# Start all services
docker-compose up

# Start in background
docker-compose up -d

# Stop all services
docker-compose down

# View logs
docker-compose logs                    # All services
docker-compose logs orchestrator       # Specific service
docker-compose logs -f                 # Follow logs

# Check service status
docker-compose ps

# Execute command in running container
docker-compose exec orchestrator /bin/bash

# Rebuild images
docker-compose build

# Rebuild and start
docker-compose up -d --build

# Remove volumes (cleanup)
docker-compose down -v
```

## Individual Docker Commands

### Build

```bash
# Cybersecurity agent
docker build -t cai-cybersecurity-agent ./cybersecurity-agent

# Orchestrator
docker build -t cai-orchestrator ./orchestrator-agent

# With build args
docker build -t cai-cybersecurity-agent:1.0 ./cybersecurity-agent
```

### Run

```bash
# Cybersecurity agent
docker run -d \
  --name cybersecurity-agent \
  -p 9003:9003 \
  -e DEEPSEEK_API_KEY=your-key \
  cai-cybersecurity-agent

# Orchestrator with volume
docker run -d \
  --name orchestrator \
  -p 8000:8000 \
  -v orchestrator_data:/data \
  -e DEEPSEEK_API_KEY=your-key \
  cai-orchestrator
```

### Logs

```bash
# View logs
docker logs container-name
docker logs -f container-name              # Follow logs
docker logs --tail 100 container-name      # Last 100 lines
docker logs --since 10m container-name     # Last 10 minutes
```

### Inspect

```bash
# Check container status
docker ps -a

# View container details
docker inspect container-name

# View image details
docker image inspect image-name

# Container stats
docker stats
```

## Health Checks

Both services include health checks:

```bash
# Check orchestrator health
curl http://localhost:8000/health

# Check cybersecurity agent health
curl http://localhost:9003/health

# In docker-compose
docker-compose ps
```

## Networking

### Service Discovery

Inside Docker network:
- Orchestrator: `http://orchestrator:8000`
- Cybersecurity Agent: `http://cybersecurity:9003`

From host machine:
- Orchestrator: `http://localhost:8000`
- Cybersecurity Agent: `http://localhost:9003`

### Register Agent from Host

```bash
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "cybersecurity-agent",
    "url": "http://cybersecurity:9003"
  }'
```

### Custom Networks

```bash
# Create custom network
docker network create my-cai-network

# Run containers on custom network
docker run -d \
  --network my-cai-network \
  --name orchestrator \
  cai-orchestrator

docker run -d \
  --network my-cai-network \
  --name cybersecurity-agent \
  cai-cybersecurity-agent
```

## Volumes and Persistence

### Agent Registry Persistence

The orchestrator stores agent registry in `/data/agent_registry.json`:

```bash
# With docker-compose (automatic)
docker-compose up -d
# Registry persists in `orchestrator_data` volume

# With individual docker run
docker run -d \
  -v orchestrator_data:/data \
  cai-orchestrator

# Verify volume
docker volume ls
docker volume inspect orchestrator_data
```

### Backup Registry

```bash
# Copy from container
docker cp orchestrator:/data/agent_registry.json ./agent_registry.json

# Or use volume
docker run --rm \
  -v orchestrator_data:/data \
  -v $(pwd):/backup \
  alpine cp /data/agent_registry.json /backup/
```

## Development Workflow

### Rebuild After Code Changes

```bash
# Option 1: Docker Compose
docker-compose up -d --build

# Option 2: Individual
docker build -t cai-cybersecurity-agent ./cybersecurity-agent
docker stop cybersecurity-agent
docker rm cybersecurity-agent
docker run -d \
  -p 9003:9003 \
  -e DEEPSEEK_API_KEY=your-key \
  --name cybersecurity-agent \
  cai-cybersecurity-agent
```

### Interactive Development

```bash
# Shell into running container
docker-compose exec orchestrator /bin/bash

# Run Python directly
docker-compose exec cybersecurity python -c "import config; print(config.get_config())"

# View application logs
docker-compose logs -f cybersecurity
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
docker logs container-name

# Check if port is in use
docker ps | grep port-number
lsof -i :8000  # Check port 8000
```

### Network Issues

```bash
# Inspect network
docker network inspect cai_network

# Test connectivity
docker-compose exec orchestrator ping cybersecurity
docker-compose exec cybersecurity ping orchestrator
```

### Volume Issues

```bash
# List volumes
docker volume ls

# Inspect volume
docker volume inspect orchestrator_data

# Clean up unused volumes
docker volume prune
```

### Health Check Failures

```bash
# Check health status
docker ps --format "table {{.Names}}\t{{.Status}}"

# Manual health check
curl -v http://localhost:8000/health

# Check from container
docker-compose exec orchestrator curl http://localhost:8000/health
```

## Production Deployment

### Security Best Practices

1. **Environment Variables**: Use `.env` files, never commit secrets
```bash
# .env (not in git)
DEEPSEEK_API_KEY=prod-key

# .env.example (in git)
DEEPSEEK_API_KEY=change-me
```

2. **Image Tagging**: Use specific versions
```bash
docker build -t cai-cybersecurity-agent:1.0.0 ./cybersecurity-agent
```

3. **Resource Limits**
```yaml
services:
  orchestrator:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G
```

4. **Restart Policies**
```yaml
restart_policy:
  condition: on-failure
  delay: 5s
  max_attempts: 3
  window: 120s
```

### Registry Cleanup

Periodically clean up unused images and containers:

```bash
# Remove stopped containers
docker container prune

# Remove unused images
docker image prune

# Remove unused volumes
docker volume prune

# Remove unused networks
docker network prune
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Build and Push Docker Images

on:
  push:
    branches: [main]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Build images
        run: |
          docker build -t cai-cybersecurity-agent:${{ github.sha }} ./cybersecurity-agent
          docker build -t cai-orchestrator:${{ github.sha }} ./orchestrator-agent
      
      - name: Push to registry
        run: |
          docker push cai-cybersecurity-agent:${{ github.sha }}
          docker push cai-orchestrator:${{ github.sha }}
```

## See Also

- [README.md](README.md) - Project overview
- [CONFIGURATION.md](CONFIGURATION.md) - Configuration reference
- [DYNAMIC_REGISTRATION.md](DYNAMIC_REGISTRATION.md) - Agent registration API

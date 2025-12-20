# Building Docker Images

## Quick Build Guide

### Option 1: Build from Root Directory (Recommended)

```bash
# From project root directory
cd /path/to/7.0.1-cai-cybersecurity-agent

# Build both images
docker build -t cai-cybersecurity-agent:v1 -f cybersecurity-agent/Dockerfile .
docker build -t cai-orchestrator:v1 -f orchestrator-agent/Dockerfile .

# Or with docker-compose (automatic)
docker-compose build

# Or with custom image names
docker-compose build --image-name-prefix myregistry/
```

### Option 2: Build from Agent Directory

```bash
# Build cybersecurity agent from its directory
cd cybersecurity-agent
docker build -t cai-cybersecurity-agent:v1 -f Dockerfile.local .

# Build orchestrator from its directory
cd ../orchestrator-agent
docker build -t cai-orchestrator:v1 -f Dockerfile.local .
```

### Option 3: Build for Docker Hub Registry

```bash
# From root directory
docker build -t myusername/cai-cybersecurity-agent:v1 -f cybersecurity-agent/Dockerfile .
docker build -t myusername/cai-orchestrator:v1 -f orchestrator-agent/Dockerfile .

# Push to Docker Hub
docker push myusername/cai-cybersecurity-agent:v1
docker push myusername/cai-orchestrator:v1
```

---

## Dockerfile Files Explained

### Root-Level Dockerfiles

**`cybersecurity-agent/Dockerfile`** - For use with docker-compose
- Designed to be built from project root
- Copies from root `requirements.txt`
- Used by `docker-compose.yml`
- Context: project root directory

**`orchestrator-agent/Dockerfile`** - For use with docker-compose
- Designed to be built from project root
- Copies from root `requirements.txt`
- Used by `docker-compose.yml`
- Context: project root directory

### Agent-Level Dockerfiles

**`cybersecurity-agent/Dockerfile.local`** - For standalone builds
- Can be built from agent directory
- Includes all dependencies locally
- Useful for CI/CD pipelines
- Context: agent directory

**`orchestrator-agent/Dockerfile.local`** - For standalone builds
- Can be built from agent directory
- Includes all dependencies locally
- Useful for CI/CD pipelines
- Context: agent directory

---

## Common Build Commands

### Build Single Agent
```bash
# From root
docker build -t cai-cybersecurity-agent -f cybersecurity-agent/Dockerfile .

# From agent directory
cd cybersecurity-agent
docker build -t cai-cybersecurity-agent -f Dockerfile.local .
```

### Build with Tags
```bash
# Simple tag
docker build -t myapp/agent:v1.0.0 .

# Multiple tags
docker build -t myapp/agent:v1.0.0 -t myapp/agent:latest .

# With build args
docker build -t myapp/agent:v1.0.0 \
  --build-arg VERSION=1.0.0 \
  --build-arg BUILD_DATE=$(date -u +'%Y-%m-%dT%H:%M:%SZ') .
```

### Build with Custom Base Image
```bash
# Use different Python version
docker build \
  --build-arg PYTHON_VERSION=3.12 \
  -t cai-cybersecurity-agent:py312 \
  -f cybersecurity-agent/Dockerfile .
```

---

## Build All Images

### Using Docker Compose
```bash
# Build all services
docker-compose build

# Build specific service
docker-compose build orchestrator
docker-compose build cybersecurity

# Build with no cache
docker-compose build --no-cache

# Build and start
docker-compose up -d --build
```

### Using Shell Script
```bash
#!/bin/bash

echo "Building cybersecurity agent..."
docker build -t cai-cybersecurity-agent:latest \
  -f cybersecurity-agent/Dockerfile .

echo "Building orchestrator..."
docker build -t cai-orchestrator:latest \
  -f orchestrator-agent/Dockerfile .

echo "Build complete!"
docker images | grep cai
```

---

## Image Optimization

### Multi-Stage Build Benefits

The Dockerfiles use multi-stage builds:

1. **Builder Stage**: Installs all build dependencies
   - Large build tools included
   - Virtual environment created
   - Packages compiled

2. **Runtime Stage**: Copies only what's needed
   - Only virtual environment copied
   - Build tools excluded
   - Smaller final image

### Resulting Image Sizes
```
cybersecurity-agent: ~400-500MB
orchestrator: ~400-500MB
```

### Further Optimization

```dockerfile
# Option 1: Use Alpine (smaller base)
FROM python:3.11-alpine

# Option 2: Use distroless
FROM gcr.io/distroless/python3.11

# Option 3: Custom slim with only needed packages
FROM python:3.11-slim
RUN apt-get install -y --no-install-recommends <specific-packages>
```

---

## Build Matrix (All Combinations)

### Build from Root (Docker Compose)
```bash
docker-compose build
```
✅ Recommended for production
✅ Uses docker-compose.yml
✅ All services together

### Build from Root (Manual)
```bash
docker build -t cai-cybersecurity-agent -f cybersecurity-agent/Dockerfile .
docker build -t cai-orchestrator -f orchestrator-agent/Dockerfile .
```
✅ Full control over images
✅ Can use custom tags
✅ Good for CI/CD

### Build from Agent Directory
```bash
cd cybersecurity-agent && docker build -t cai-cybersecurity-agent -f Dockerfile.local .
cd orchestrator-agent && docker build -t cai-orchestrator -f Dockerfile.local .
```
✅ Simpler commands
✅ Works from agent dir
✅ Good for development

---

## Troubleshooting Build Issues

### "No such file or directory"
**Error**: `failed to compute cache key: "/cybersecurity-agent" not found`

**Cause**: Building from wrong directory or using wrong Dockerfile

**Solution**:
```bash
# Option 1: Build from root with Dockerfile
cd /path/to/project/root
docker build -t cai-cybersecurity-agent -f cybersecurity-agent/Dockerfile .

# Option 2: Build from agent dir with Dockerfile.local
cd cybersecurity-agent
docker build -t cai-cybersecurity-agent -f Dockerfile.local .
```

### Build Takes Too Long
**Cause**: No cache or large dependencies

**Solution**:
```bash
# Use cache
docker build -t cai-cybersecurity-agent -f cybersecurity-agent/Dockerfile .

# Check cache
docker system df

# Use buildkit (faster)
DOCKER_BUILDKIT=1 docker build -t cai-cybersecurity-agent -f cybersecurity-agent/Dockerfile .
```

### Out of Disk Space
**Cause**: Large intermediate images

**Solution**:
```bash
# Clean up unused images
docker image prune

# Clean everything
docker system prune -a

# Check disk usage
docker system df
```

### Requirements Installation Fails
**Cause**: Missing dependencies or network issues

**Solution**:
```bash
# Build with verbose output
docker build --progress=plain -t cai-cybersecurity-agent -f cybersecurity-agent/Dockerfile .

# Check requirements.txt exists
ls -la requirements.txt cybersecurity-agent/

# Rebuild without cache
docker build --no-cache -t cai-cybersecurity-agent -f cybersecurity-agent/Dockerfile .
```

---

## Docker Build Best Practices

### 1. Always Tag Images
```bash
docker build -t myapp/agent:v1.0.0 -t myapp/agent:latest .
```

### 2. Use .dockerignore
✅ Already included in project

### 3. Minimize Layers
```dockerfile
# Bad: Many RUN commands
RUN apt-get update
RUN apt-get install -y package1
RUN apt-get install -y package2

# Good: Single RUN command
RUN apt-get update && apt-get install -y \
    package1 \
    package2 \
    && rm -rf /var/lib/apt/lists/*
```

### 4. Order Dockerfile Statements
- Base image
- System packages
- Python dependencies
- Application code
- Configuration
- Entry point

### 5. Use BuildKit for Speed
```bash
DOCKER_BUILDKIT=1 docker build -t myapp/agent .
```

---

## CI/CD Integration

### GitHub Actions
```yaml
name: Build Docker Images

on:
  push:
    branches: [main]
    tags: ['v*']

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Build cybersecurity agent
        uses: docker/build-push-action@v4
        with:
          context: .
          file: ./cybersecurity-agent/Dockerfile
          tags: myregistry/cai-cybersecurity-agent:latest
          push: false

      - name: Build orchestrator
        uses: docker/build-push-action@v4
        with:
          context: .
          file: ./orchestrator-agent/Dockerfile
          tags: myregistry/cai-orchestrator:latest
          push: false
```

### GitLab CI
```yaml
docker_build:
  stage: build
  image: docker:latest
  services:
    - docker:dind
  script:
    - docker build -t cai-cybersecurity-agent -f cybersecurity-agent/Dockerfile .
    - docker build -t cai-orchestrator -f orchestrator-agent/Dockerfile .
```

---

## Image Inspection

### View Image Info
```bash
docker image inspect cai-cybersecurity-agent
docker history cai-cybersecurity-agent
docker run --rm cai-cybersecurity-agent python --version
```

### Check Image Layers
```bash
docker history --human --no-trunc cai-cybersecurity-agent
```

### Verify Health Check
```bash
docker run -it cai-cybersecurity-agent /bin/bash
curl http://localhost:9003/health
```

---

## Build Summary

| Method | Location | Best For |
|--------|----------|----------|
| `docker-compose build` | Root | Production, docker-compose |
| `docker build -f Dockerfile` | Root | CI/CD, full control |
| `docker build -f Dockerfile.local` | Agent dir | Development, simplicity |
| Manual docker-compose | Root | Custom config |

---

See Also:
- [DOCKER.md](DOCKER.md) - Complete Docker guide
- [docker-compose.yml](docker-compose.yml) - Service config
- [README.md](README.md) - Project overview

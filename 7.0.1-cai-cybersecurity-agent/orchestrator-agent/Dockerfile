# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements.txt .
COPY orchestrator-agent/requirements.txt ./orchestrator-agent/

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt && \
    pip install -r orchestrator-agent/requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY requirements.txt .
COPY orchestrator-agent/ ./orchestrator-agent/

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Set working directory for the agent
WORKDIR /app/orchestrator-agent

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${ORCHESTRATOR_REGISTRY_PORT:-8000}/health || exit 1

# Default environment variables
ENV ORCHESTRATOR_REGISTRY_HOST=0.0.0.0 \
    ORCHESTRATOR_REGISTRY_PORT=8000 \
    AGENT_REGISTRY_FILE=/data/agent_registry.json

# Create data volume for registry
VOLUME ["/data"]

# Expose port
EXPOSE 8000

# Run the agent
CMD ["python", "orchestrator.py"]

# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements files
COPY requirements.txt .
COPY cybersecurity-agent/requirements.txt ./cybersecurity-agent/

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt && \
    pip install -r cybersecurity-agent/requirements.txt

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
COPY cybersecurity-agent/ ./cybersecurity-agent/

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Set working directory for the agent
WORKDIR /app/cybersecurity-agent

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${CYBERSECURITY_AGENT_PORT:-9003}/health || exit 1

# Default environment variables
ENV CYBERSECURITY_AGENT_HOST=0.0.0.0 \
    CYBERSECURITY_AGENT_PORT=9003

# Expose port
EXPOSE 9003

# Run the agent
CMD ["python", "server.py"]

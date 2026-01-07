FROM python:3.11-slim as base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Development stage
FROM base as development

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    httpx \
    black \
    flake8 \
    mypy

# Create non-root user
RUN useradd -m -u 1000 cai && chown -R cai:cai /app
USER cai

# Copy the entire application structure
COPY --chown=cai:cai . .

EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--log-level", "debug"]

# Production stage
FROM base as production

# Copy the application code
COPY . .

# Setup storage
RUN mkdir -p /app/storage && \
    chmod -R 777 /app/storage && \
    touch /app/storage/scans_results.json

# Pass environment variables from host or .env file
ENV WEBHOOK_URL="" \
    DEEPSEEK_API_KEY="" \
    OPENAI_API_KEY="" \
    CAI_MODEL="" \
    CAI_AGENT_TYPE="" \
    API_BASE=""

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "debug"]

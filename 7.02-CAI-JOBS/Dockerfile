FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY app/ ./app
COPY ui/ ./ui

# Pass environment variables from host or .env file
ENV WEBHOOK_URL=""
ENV DEEPSEEK_API_KEY=""
ENV OPENAI_API_KEY=""
ENV CAI_MODEL=""
ENV CAI_AGENT_TYPE=""
ENV API_BASE=""

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

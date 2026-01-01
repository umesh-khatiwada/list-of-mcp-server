FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir psutil requests

# Copy source code
COPY main.py .

# Run the agent
CMD ["python", "main.py"]

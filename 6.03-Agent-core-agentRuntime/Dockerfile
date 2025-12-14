# Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y curl gcc python3-dev libffi-dev libssl-dev && rm -rf /var/lib/apt/lists/*

# Install pip dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your app source code
COPY . .

# Start the FastAPI server
CMD ["uvicorn", "app.server:app", "--host", "0.0.0.0", "--port", "8000"]

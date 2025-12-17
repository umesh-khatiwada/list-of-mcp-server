#!/bin/bash

# Red Team Agent Local Runner
# Runs the red team agent on port 9093 and registers with orchestrator

set -e

echo "=========================================="
echo "Red Team Agent - Local Setup"
echo "=========================================="
echo ""

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from .env.example..."
    cp ../.env.example .env
    echo "⚠️  Please edit .env and add your API key!"
fi

# Source .env to get variables
export $(cat .env | grep -v '#' | xargs)

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Run the server
echo ""
echo "Starting Red Team Agent on port ${REDTEAM_AGENT_PORT:-9093}..."
echo ""
echo "Available at: http://localhost:${REDTEAM_AGENT_PORT:-9093}"
echo ""
echo "To register with orchestrator:"
echo "  curl -X POST http://localhost:8000/register \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"name\": \"redteam-agent\", \"url\": \"http://127.0.0.1:9093\"}'"
echo ""

python server.py

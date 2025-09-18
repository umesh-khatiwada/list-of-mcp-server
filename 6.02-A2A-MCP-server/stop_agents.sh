#!/bin/bash

# Shutdown script for A2A MCP agents
echo "Stopping A2A MCP Agent System..."

# Find and kill agent processes
MATH_AGENT_PID=$(pgrep -f "math-agent.py")
RESEARCH_AGENT_PID=$(pgrep -f "research-agent.py")
ORCHESTRATOR_PID=$(pgrep -f "orchestrator.py")

if [ ! -z "$MATH_AGENT_PID" ]; then
    echo "Stopping math agent (PID: $MATH_AGENT_PID)..."
    kill $MATH_AGENT_PID
fi

if [ ! -z "$RESEARCH_AGENT_PID" ]; then
    echo "Stopping research agent (PID: $RESEARCH_AGENT_PID)..."
    kill $RESEARCH_AGENT_PID
fi

if [ ! -z "$ORCHESTRATOR_PID" ]; then
    echo "Stopping orchestrator (PID: $ORCHESTRATOR_PID)..."
    kill $ORCHESTRATOR_PID
fi

# Wait a moment for processes to terminate
sleep 2

# Force kill if still running
pkill -9 -f "agent.py" 2>/dev/null
pkill -9 -f "orchestrator.py" 2>/dev/null

echo "All agents stopped."

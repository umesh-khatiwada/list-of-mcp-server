#!/bin/bash

# Startup script for A2A MCP agents
echo "Starting A2A MCP Agent System..."

# Activate virtual environment if it exists
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Check if agents are already running
MATH_AGENT_PID=$(pgrep -f "math-agent.py")
RESEARCH_AGENT_PID=$(pgrep -f "research-agent.py")

if [ ! -z "$MATH_AGENT_PID" ]; then
    echo "Math agent is already running (PID: $MATH_AGENT_PID)"
else
    echo "Starting stable math agent..."
    python3 math-agent/stable-math-agent.py &
    MATH_AGENT_NEW_PID=$!
    echo "Math agent started (PID: $MATH_AGENT_NEW_PID)"
fi

if [ ! -z "$RESEARCH_AGENT_PID" ]; then
    echo "Research agent is already running (PID: $RESEARCH_AGENT_PID)"
else
    echo "Starting research agent..."
    python3 research-agent/research-agent.py &
    RESEARCH_AGENT_NEW_PID=$!
    echo "Research agent started (PID: $RESEARCH_AGENT_NEW_PID)"
fi

# Wait a moment for agents to initialize
echo "Waiting for agents to initialize..."
sleep 3

echo "Agents should now be running. You can start the orchestrator with:"
echo "python3 orchestrator-agent/orchestrator.py"
echo ""
echo "To stop all agents, run: pkill -f 'agent.py'"

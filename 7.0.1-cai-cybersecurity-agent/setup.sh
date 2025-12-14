#!/bin/bash
# Quick setup and agent registration script for the orchestrator

set -e

ORCHESTRATOR_URL="${ORCHESTRATOR_URL:-http://localhost:8000}"
ORCHESTRATOR_REGISTRY_HOST="${ORCHESTRATOR_REGISTRY_HOST:-127.0.0.1}"
ORCHESTRATOR_REGISTRY_PORT="${ORCHESTRATOR_REGISTRY_PORT:-8000}"

echo "========================================"
echo "Agent Registration Utility"
echo "========================================"
echo ""

# Show help
if [[ "$1" == "help" ]] || [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
    echo "Usage: ./setup.sh [command] [args...]"
    echo ""
    echo "Commands:"
    echo "  register <name> <url>     Register an agent"
    echo "  list                      List all registered agents"
    echo "  get <name>               Get specific agent details"
    echo "  unregister <name>        Unregister an agent"
    echo "  health                   Check registry health"
    echo "  orchestrator             Start orchestrator"
    echo "  cybersecurity            Start cybersecurity agent"
    echo "  all                      Start all services"
    echo "  help                     Show this help"
    echo ""
    echo "Environment Variables:"
    echo "  ORCHESTRATOR_URL         Registry URL (default: http://localhost:8000)"
    echo "  ORCHESTRATOR_REGISTRY_HOST  Registry host (default: 127.0.0.1)"
    echo "  ORCHESTRATOR_REGISTRY_PORT  Registry port (default: 8000)"
    echo ""
    echo "Examples:"
    echo "  # Register cybersecurity agent"
    echo "  ./setup.sh register cybersecurity-agent http://127.0.0.1:9003"
    echo ""
    echo "  # List all agents"
    echo "  ./setup.sh list"
    echo ""
    echo "  # Check health"
    echo "  ./setup.sh health"
    exit 0
fi

# Register agent
if [[ "$1" == "register" ]]; then
    if [[ -z "$2" ]] || [[ -z "$3" ]]; then
        echo "Error: register requires name and url arguments"
        echo "Usage: ./setup.sh register <name> <url>"
        exit 1
    fi
    
    echo "Registering agent: $2 at $3"
    curl -X POST "${ORCHESTRATOR_URL}/register" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"$2\", \"url\": \"$3\"}" \
        -s | python3 -m json.tool
    echo ""
    exit 0
fi

# List agents
if [[ "$1" == "list" ]]; then
    echo "Fetching registered agents from ${ORCHESTRATOR_URL}/agents"
    curl -s "${ORCHESTRATOR_URL}/agents" | python3 -m json.tool
    echo ""
    exit 0
fi

# Get specific agent
if [[ "$1" == "get" ]]; then
    if [[ -z "$2" ]]; then
        echo "Error: get requires agent name argument"
        echo "Usage: ./setup.sh get <name>"
        exit 1
    fi
    
    echo "Fetching agent: $2"
    curl -s "${ORCHESTRATOR_URL}/agents/$2" | python3 -m json.tool
    echo ""
    exit 0
fi

# Unregister agent
if [[ "$1" == "unregister" ]]; then
    if [[ -z "$2" ]]; then
        echo "Error: unregister requires agent name argument"
        echo "Usage: ./setup.sh unregister <name>"
        exit 1
    fi
    
    echo "Unregistering agent: $2"
    curl -X DELETE "${ORCHESTRATOR_URL}/unregister/$2" -s | python3 -m json.tool
    echo ""
    exit 0
fi

# Health check
if [[ "$1" == "health" ]]; then
    echo "Checking registry health at ${ORCHESTRATOR_URL}/health"
    curl -s "${ORCHESTRATOR_URL}/health" | python3 -m json.tool
    echo ""
    exit 0
fi

# Start orchestrator
if [[ "$1" == "orchestrator" ]]; then
    echo "Starting Orchestrator..."
    echo "Registry will be available at http://${ORCHESTRATOR_REGISTRY_HOST}:${ORCHESTRATOR_REGISTRY_PORT}"
    cd orchestrator-agent
    python orchestrator.py
    exit $?
fi

# Start cybersecurity agent
if [[ "$1" == "cybersecurity" ]]; then
    echo "Starting Cybersecurity Agent..."
    cd cybersecurity-agent
    python server.py
    exit $?
fi

# Start all services
if [[ "$1" == "all" ]]; then
    echo "Starting all services..."
    echo ""
    
    # Start orchestrator in background
    echo "Starting Orchestrator..."
    cd orchestrator-agent
    python orchestrator.py &
    ORCHESTRATOR_PID=$!
    echo "Orchestrator PID: $ORCHESTRATOR_PID"
    cd ..
    
    sleep 2
    
    # Start cybersecurity agent in background
    echo ""
    echo "Starting Cybersecurity Agent..."
    cd cybersecurity-agent
    python server.py &
    CYBERSECURITY_PID=$!
    echo "Cybersecurity Agent PID: $CYBERSECURITY_PID"
    cd ..
    
    sleep 2
    
    # Register cybersecurity agent
    echo ""
    echo "Registering Cybersecurity Agent with Orchestrator..."
    curl -X POST "http://${ORCHESTRATOR_REGISTRY_HOST}:${ORCHESTRATOR_REGISTRY_PORT}/register" \
        -H "Content-Type: application/json" \
        -d '{"name": "cybersecurity-agent", "url": "http://127.0.0.1:9003"}' \
        -s | python3 -m json.tool
    
    echo ""
    echo "========================================"
    echo "All services started!"
    echo "========================================"
    echo ""
    echo "Orchestrator: Running (PID: $ORCHESTRATOR_PID)"
    echo "Registry API: http://${ORCHESTRATOR_REGISTRY_HOST}:${ORCHESTRATOR_REGISTRY_PORT}"
    echo ""
    echo "Cybersecurity Agent: Running (PID: $CYBERSECURITY_PID)"
    echo "Agent URL: http://127.0.0.1:9003"
    echo ""
    echo "To stop services:"
    echo "  kill $ORCHESTRATOR_PID $CYBERSECURITY_PID"
    echo ""
    
    # Wait for services to finish
    wait
    exit 0
fi

# If no command, show usage
echo "No command specified. Use './setup.sh help' for usage information."
echo ""
echo "Quick commands:"
echo "  ./setup.sh orchestrator           - Start orchestrator"
echo "  ./setup.sh cybersecurity          - Start cybersecurity agent"
echo "  ./setup.sh all                    - Start all services"
echo "  ./setup.sh register <name> <url>  - Register an agent"
echo "  ./setup.sh list                   - List registered agents"
echo "  ./setup.sh health                 - Check registry health"

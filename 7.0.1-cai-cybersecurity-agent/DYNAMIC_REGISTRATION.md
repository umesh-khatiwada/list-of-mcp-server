# Dynamic Agent Registration Guide

## Overview

Instead of hardcoding agent URLs in environment variables, the orchestrator now supports **dynamic agent registration** via HTTP endpoints. Agents can self-register at runtime without any configuration changes.

## How It Works

### 1. **Registry Service**
The orchestrator exposes an HTTP API for agent management:
- **Host**: `127.0.0.1` (configurable via `ORCHESTRATOR_REGISTRY_HOST`)
- **Port**: `8000` (configurable via `ORCHESTRATOR_REGISTRY_PORT`)
- **Storage**: `agent_registry.json` (persists registrations)

### 2. **Registration Flow**
```
Agent Startup → Register with Orchestrator → Agent becomes available
               POST /register
```

### 3. **Discovery**
When the orchestrator starts, it loads agents from the registry and dynamically updates its capabilities.

## API Endpoints

### Register Agent
Register a new agent with the orchestrator.

```bash
POST /register
Content-Type: application/json

{
  "name": "cybersecurity-agent",
  "url": "http://127.0.0.1:9003"
}
```

**Response:**
```json
{
  "name": "cybersecurity-agent",
  "url": "http://127.0.0.1:9003"
}
```

**Example with curl:**
```bash
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "cybersecurity-agent",
    "url": "http://127.0.0.1:9003"
  }'
```

### List All Agents
Get all registered agents.

```bash
GET /agents
```

**Response:**
```json
{
  "agents": {
    "cybersecurity-agent": "http://127.0.0.1:9003",
    "compliance-agent": "http://127.0.0.1:9004"
  },
  "count": 2
}
```

**Example:**
```bash
curl http://localhost:8000/agents
```

### Get Specific Agent
Get details of a single agent.

```bash
GET /agents/{agent_name}
```

**Response:**
```json
{
  "name": "cybersecurity-agent",
  "url": "http://127.0.0.1:9003"
}
```

**Example:**
```bash
curl http://localhost:8000/agents/cybersecurity-agent
```

### Unregister Agent
Remove an agent from the registry.

```bash
DELETE /unregister/{agent_name}
```

**Response:**
```json
{
  "message": "Agent 'cybersecurity-agent' unregistered"
}
```

**Example:**
```bash
curl -X DELETE http://localhost:8000/unregister/cybersecurity-agent
```

### Health Check
Check registry service status.

```bash
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "registered_agents": 1
}
```

**Example:**
```bash
curl http://localhost:8000/health
```

## Quick Start Guide

### Step 1: Start Orchestrator
```bash
python orchestrator-agent/orchestrator.py
```

Output:
```
Starting Agent Registry API on 127.0.0.1:8000
Registry service started on http://127.0.0.1:8000
Register agents via: POST http://127.0.0.1:8000/register
List agents via: GET http://127.0.0.1:8000/agents
```

### Step 2: Start Cybersecurity Agent (in another terminal)
```bash
cd cybersecurity-agent
python server.py
```

### Step 3: Register the Agent
```bash
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "cybersecurity-agent",
    "url": "http://127.0.0.1:9003"
  }'
```

### Step 4: Verify Registration
```bash
curl http://localhost:8000/agents
```

Response:
```json
{
  "agents": {
    "cybersecurity-agent": "http://127.0.0.1:9003"
  },
  "count": 1
}
```

### Step 5: Use the Orchestrator
The orchestrator now has the cybersecurity agent available. You can ask security questions and it will route them appropriately.

## Configuration

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `ORCHESTRATOR_REGISTRY_HOST` | `127.0.0.1` | Registry service host |
| `ORCHESTRATOR_REGISTRY_PORT` | `8000` | Registry service port |
| `AGENT_REGISTRY_FILE` | `agent_registry.json` | File storing registered agents |

### Example .env
```bash
ORCHESTRATOR_REGISTRY_HOST=0.0.0.0  # Listen on all interfaces
ORCHESTRATOR_REGISTRY_PORT=8000
AGENT_REGISTRY_FILE=/var/lib/agent_registry.json
```

## Registry File Format

The `agent_registry.json` file stores registered agents:

```json
{
  "agents": {
    "cybersecurity-agent": "http://127.0.0.1:9003",
    "compliance-agent": "http://127.0.0.1:9004",
    "threat-intel-agent": "http://192.168.1.100:9005"
  }
}
```

This file persists across restarts, so agents remain registered even after shutdown.

## Multi-Agent Setup Example

### Terminal 1: Orchestrator
```bash
python orchestrator-agent/orchestrator.py
```

### Terminal 2: Cybersecurity Agent
```bash
cd cybersecurity-agent && python server.py
```

### Terminal 3: Compliance Agent (example)
```bash
cd compliance-agent && python server.py
```

### Terminal 4: Register Agents
```bash
# Register cybersecurity agent
curl -X POST http://localhost:8000/register \
  -d '{"name": "cybersecurity-agent", "url": "http://127.0.0.1:9003"}'

# Register compliance agent
curl -X POST http://localhost:8000/register \
  -d '{"name": "compliance-agent", "url": "http://127.0.0.1:9004"}'

# List all agents
curl http://localhost:8000/agents
```

## Backward Compatibility

The system still supports the legacy configuration method for backward compatibility:

**Legacy (still works):**
```bash
export CYBERSECURITY_AGENT_URL=http://127.0.0.1:9003
python orchestrator-agent/orchestrator.py
```

**Modern (recommended):**
```bash
python orchestrator-agent/orchestrator.py
# Then register via API:
curl -X POST http://localhost:8000/register \
  -d '{"name": "cybersecurity-agent", "url": "http://127.0.0.1:9003"}'
```

**Precedence:**
1. **Agent Registry File** (`agent_registry.json`) - takes precedence
2. **Environment Variables** - used if registry is empty
3. **Defaults** - empty if neither is set

## Use Cases

### 1. **Dynamic Multi-Agent System**
Add/remove agents at runtime without restarting orchestrator.

### 2. **Blue-Green Deployment**
Register new agent version, test it, then unregister old version.

### 3. **Scaling**
Dynamically register additional agent instances as load increases.

### 4. **Development**
Keep orchestrator running, restart and re-register agents during development.

### 5. **Microservices Architecture**
Agents register themselves when they start, orchestrator auto-discovers them.

## Advanced: Auto-Registration Script

Create a script that agents run on startup to auto-register:

```python
import requests
import os

def register_with_orchestrator():
    """Register this agent with the orchestrator."""
    orchestrator_registry = os.getenv(
        "ORCHESTRATOR_REGISTRY_URL",
        "http://127.0.0.1:8000"
    )

    agent_name = os.getenv("AGENT_NAME", "my-agent")
    agent_url = os.getenv("AGENT_URL", "http://127.0.0.1:9003")

    response = requests.post(
        f"{orchestrator_registry}/register",
        json={"name": agent_name, "url": agent_url}
    )

    if response.status_code == 200:
        print(f"Registered with orchestrator: {agent_name}")
    else:
        print(f"Failed to register: {response.text}")

# Call this in your agent's startup
if __name__ == "__main__":
    register_with_orchestrator()
```

## Troubleshooting

### Registry service won't start
**Problem:** Port 8000 already in use

**Solution:**
```bash
# Use different port
export ORCHESTRATOR_REGISTRY_PORT=8001
python orchestrator-agent/orchestrator.py
```

### Agent shows as registered but not responding
**Problem:** Agent URL is incorrect or agent isn't running

**Solution:**
1. Verify agent is running
2. Verify URL is reachable: `curl http://agent-url/health`
3. Unregister and re-register with correct URL

### Changes not persisting across restarts
**Problem:** `agent_registry.json` not found or not writable

**Solution:**
```bash
# Check file permissions
ls -la agent_registry.json

# Create with proper permissions
touch agent_registry.json
chmod 644 agent_registry.json
```

### Lost agent registry
**Problem:** `agent_registry.json` deleted accidentally

**Solution:**
```bash
# Just re-register agents:
curl -X POST http://localhost:8000/register \
  -d '{"name": "agent1", "url": "http://127.0.0.1:9003"}'
```

## Architecture Diagram

```
┌─────────────────────────────────────┐
│      Orchestrator                   │
│  ┌───────────────────────────────┐  │
│  │  Agent Registry Service (API) │  │
│  │  Host: 127.0.0.1:8000         │  │
│  │  - /register                  │  │
│  │  - /agents                    │  │
│  │  - /unregister                │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │  agent_registry.json          │  │
│  │  {agents: {...}}              │  │
│  └───────────────────────────────┘  │
│  ┌───────────────────────────────┐  │
│  │  A2A Client & Tools           │  │
│  │  (uses registered agents)     │  │
│  └───────────────────────────────┘  │
└─────────────────────────────────────┘
         ↑                   ↑
         │ POST /register    │ A2A Protocol
         │                   │
    ┌────────────┐      ┌─────────────┐
    │ Agent 1    │      │ Agent 2     │
    │ (register) │      │ (register)  │
    └────────────┘      └─────────────┘
```

## See Also

- [CONFIGURATION.md](CONFIGURATION.md) - Environment variables reference
- `orchestrator-agent/config.py` - Configuration module
- `orchestrator-agent/agent_registry_service.py` - Registry service code

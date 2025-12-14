# Quick Reference - Dynamic Agent Registration

## One-Liner Setup (Recommended)
```bash
./setup.sh all
```
This starts both the orchestrator and cybersecurity agent with automatic registration.

---

## Manual Setup

### Terminal 1: Start Orchestrator with Registry
```bash
python orchestrator-agent/orchestrator.py
```
✅ Registry API ready at: `http://127.0.0.1:8000`

### Terminal 2: Start Cybersecurity Agent
```bash
cd cybersecurity-agent && python server.py
```
✅ Agent running at: `http://127.0.0.1:9003`

### Terminal 3: Register Agent
```bash
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "cybersecurity-agent",
    "url": "http://127.0.0.1:9003"
  }'
```
✅ Agent registered and available to orchestrator

---

## Key Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/register` | POST | Register an agent |
| `/agents` | GET | List all registered agents |
| `/agents/{name}` | GET | Get specific agent |
| `/unregister/{name}` | DELETE | Remove an agent |
| `/health` | GET | Check registry status |

---

## Setup Script Commands

```bash
./setup.sh orchestrator              # Start orchestrator
./setup.sh cybersecurity             # Start cybersecurity agent
./setup.sh all                       # Start all services
./setup.sh register agent1 url1      # Register agent1 at url1
./setup.sh list                      # List all registered agents
./setup.sh get agent1                # Get agent1 details
./setup.sh unregister agent1         # Remove agent1
./setup.sh health                    # Check registry health
./setup.sh help                      # Show help
```

---

## Configuration

### No Configuration Needed!
Just register agents via API. For environment variables:

```bash
cp .env.example .env
# Edit .env if needed (API keys, ports, etc.)
```

---

## Agent Registry File

Agents are stored in `agent_registry.json`:

```json
{
  "agents": {
    "cybersecurity-agent": "http://127.0.0.1:9003",
    "other-agent": "http://192.168.1.100:9004"
  }
}
```

This file persists across restarts!

---

## Example: Register Multiple Agents

```bash
# Agent 1
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"name": "cybersecurity", "url": "http://127.0.0.1:9003"}'

# Agent 2
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"name": "compliance", "url": "http://127.0.0.1:9004"}'

# List all
curl http://localhost:8000/agents
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 8000 in use | `export ORCHESTRATOR_REGISTRY_PORT=8001` |
| Agent not responding | Check: `curl http://agent-url:port/health` |
| Registry file lost | Just re-register: `./setup.sh register agent url` |
| API key errors | Set: `export DEEPSEEK_API_KEY=your-key` |

---

## Environment Variables

### Essential
```bash
DEEPSEEK_API_KEY=your-key              # Required
ORCHESTRATOR_REGISTRY_PORT=8000        # Registry port
CYBERSECURITY_AGENT_PORT=9003          # Agent port
```

### Optional
```bash
ORCHESTRATOR_REGISTRY_HOST=127.0.0.1   # Registry host
AGENT_REGISTRY_FILE=agent_registry.json # Registry file
AGENT_SYSTEM_PROMPT=...                # Custom prompt
```

See [CONFIGURATION.md](CONFIGURATION.md) for all options.

---

## Architecture

```
Orchestrator (8000)
  ├─ Registry API (/register, /agents, etc.)
  ├─ Agent Registry (agent_registry.json)
  └─ A2A Client (connects to agents)
       ↓ (A2A Protocol)
  Cybersecurity Agent (9003)
```

---

## API Examples

### Register
```bash
curl -X POST http://localhost:8000/register \
  -d '{"name":"sec-agent","url":"http://127.0.0.1:9003"}'
```

### List
```bash
curl http://localhost:8000/agents
```

### Get
```bash
curl http://localhost:8000/agents/sec-agent
```

### Unregister
```bash
curl -X DELETE http://localhost:8000/unregister/sec-agent
```

### Health
```bash
curl http://localhost:8000/health
```

---

## Complete Workflow

1. **Start All**: `./setup.sh all`
2. **Verify**: `./setup.sh list`
3. **Ask Questions**: Type in terminal 1
4. **Add Agent**: `./setup.sh register new-agent http://url`
5. **Remove Agent**: `./setup.sh unregister new-agent`
6. **Stop**: Press Ctrl+C

---

## Documentation Files

- **[README.md](README.md)** - Overview and quick start
- **[CONFIGURATION.md](CONFIGURATION.md)** - All environment variables
- **[DYNAMIC_REGISTRATION.md](DYNAMIC_REGISTRATION.md)** - Registry API details
- **[QUICKREF.md](QUICKREF.md)** - This file

---

## Next Steps

1. ✅ Run: `./setup.sh all`
2. ✅ Register agents: `./setup.sh register agent-name url`
3. ✅ Query orchestrator: Type in terminal 1
4. ✅ Check docs: [DYNAMIC_REGISTRATION.md](DYNAMIC_REGISTRATION.md)

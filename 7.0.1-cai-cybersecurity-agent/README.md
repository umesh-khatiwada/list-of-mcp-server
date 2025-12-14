# CAI Cybersecurity Agent - Multi-Agent Orchestration System

A production-ready multi-agent system for cybersecurity operations with dynamic agent registration, flexible configuration, and A2A protocol support.

## Features

✅ **Dynamic Agent Registration** - Register agents via HTTP API without configuration changes  
✅ **Flexible Configuration** - All settings via environment variables with sensible defaults  
✅ **Multi-Agent Orchestration** - Intelligent routing of security requests to specialized agents  
✅ **A2A Protocol** - Agent-to-Agent communication via Strands framework  
✅ **Persistent Registry** - Agent registrations persist across restarts  
✅ **Backward Compatible** - Legacy environment variable configuration still supported  
✅ **Production Ready** - Async/await, error handling, logging, and type safety

## Quick Start

### 1. Using the Setup Script (Recommended)

```bash
# Make setup script executable
chmod +x setup.sh

# Start all services
./setup.sh all
```

This will:
1. Start the orchestrator with registry service (port 8000)
2. Start the cybersecurity agent (port 9003)
3. Auto-register the cybersecurity agent

### 2. Manual Setup

**Terminal 1 - Start Orchestrator:**
```bash
python orchestrator-agent/orchestrator.py
```

**Terminal 2 - Start Cybersecurity Agent:**
```bash
cd cybersecurity-agent
python server.py
```

**Terminal 3 - Register Agent:**
```bash
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"name": "cybersecurity-agent", "url": "http://127.0.0.1:9003"}'
```

**Terminal 1 - You can now ask questions:**
```
> What are the OWASP top 10 vulnerabilities?
```

## Configuration

### Environment Variables

All configuration is done via environment variables. Copy and customize:

```bash
cp .env.example .env
# Edit .env with your settings
```

**Key Variables:**
- `DEEPSEEK_API_KEY` - DeepSeek API key (required)
- `ORCHESTRATOR_REGISTRY_PORT` - Registry service port (default: 8000)
- `AGENT_REGISTRY_FILE` - Registry file path (default: agent_registry.json)
- `CYBERSECURITY_AGENT_PORT` - Cybersecurity agent port (default: 9003)

See [CONFIGURATION.md](CONFIGURATION.md) for all options.

## Dynamic Agent Registration

### Register an Agent

```bash
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "cybersecurity-agent",
    "url": "http://127.0.0.1:9003"
  }'
```

### List Registered Agents

```bash
curl http://localhost:8000/agents
```

### Unregister an Agent

```bash
curl -X DELETE http://localhost:8000/unregister/cybersecurity-agent
```

See [DYNAMIC_REGISTRATION.md](DYNAMIC_REGISTRATION.md) for complete API documentation.

## Setup Script Usage

```bash
./setup.sh help                              # Show help
./setup.sh orchestrator                      # Start orchestrator
./setup.sh cybersecurity                     # Start cybersecurity agent
./setup.sh all                               # Start all services
./setup.sh register <name> <url>             # Register agent
./setup.sh list                              # List registered agents
./setup.sh get <name>                        # Get agent details
./setup.sh unregister <name>                 # Unregister agent
./setup.sh health                            # Check registry health
```

## Project Structure

```
.
├── cybersecurity-agent/
│   ├── server.py              # A2A server exposing agent
│   ├── cybersecurity.py       # Agent implementation
│   ├── base.py                # CAI agent base class
│   ├── config.py              # Configuration management
│   └── requirements.txt        # Dependencies
├── orchestrator-agent/
│   ├── orchestrator.py        # Multi-agent orchestrator
│   ├── config.py              # Configuration management
│   ├── agent_registry_service.py  # Registry HTTP API
│   └── requirements.txt        # Dependencies
├── requirements.txt            # Shared dependencies
├── .env.example                # Configuration template
├── CONFIGURATION.md            # Configuration guide
├── DYNAMIC_REGISTRATION.md     # Registry API documentation
├── setup.sh                    # Quick setup script
└── README.md                   # This file
```

## API Endpoints

### Registry Service (Orchestrator)
- `POST /register` - Register agent
- `GET /agents` - List all agents
- `GET /agents/{name}` - Get specific agent
- `DELETE /unregister/{name}` - Unregister agent
- `GET /health` - Health check

### Cybersecurity Agent (A2A Protocol)
- `cybersecurity_consult` - General security consultation
- `security_posture_analysis` - Assess security posture
- `threat_modeling` - Perform threat modeling
- `compliance_assessment` - Evaluate compliance

## Architecture

```
┌──────────────────────────────────────┐
│    Orchestrator                      │
│  ┌────────────────────────────────┐  │
│  │ Registry Service (8000)        │  │
│  │ - HTTP API for agent mgmt     │  │
│  │ - Persistent JSON storage     │  │
│  └────────────────────────────────┘  │
│  ┌────────────────────────────────┐  │
│  │ A2A Client & Tools             │  │
│  │ - Discovers agents             │  │
│  │ - Routes requests              │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
         ↑                    ↑
    POST /register      A2A Protocol
         │                    │
    ┌─────────────┐     ┌──────────────┐
    │ Agent 1     │     │ Agent 2      │
    │ (register)  │     │ (register)   │
    └─────────────┘     └──────────────┘
```

## Configuration Methods

### Method 1: Dynamic Registration (Recommended)
No configuration needed! Just register agents via API at runtime.

```bash
./setup.sh register agent-name http://agent-url:port
```

### Method 2: Environment Variables (Legacy)
```bash
export CYBERSECURITY_AGENT_URL=http://127.0.0.1:9003
export ORCHESTRATOR_AGENT_URLS=http://127.0.0.1:9003,http://127.0.0.1:9004
python orchestrator-agent/orchestrator.py
```

### Method 3: .env File
```bash
cp .env.example .env
# Edit .env
python orchestrator-agent/orchestrator.py
```

## Troubleshooting

### Port Already in Use
```bash
# Change port via environment variable
export ORCHESTRATOR_REGISTRY_PORT=8001
python orchestrator-agent/orchestrator.py
```

### Agent Not Discovered
1. Verify agent is running and accessible
2. Check registration: `curl http://localhost:8000/agents`
3. Check agent URL is correct and responds to health checks

### API Key Issues
```bash
# DeepSeek
export DEEPSEEK_API_KEY=your-key

# OpenAI (fallback)
export OPENAI_API_KEY=your-key
```

See [CONFIGURATION.md](CONFIGURATION.md) for more troubleshooting.

## Development

### Install Dependencies
```bash
pip install -r requirements.txt
pip install -r cybersecurity-agent/requirements.txt
pip install -r orchestrator-agent/requirements.txt
```

### Running Tests
```bash
# Health check
curl http://localhost:8000/health

# Register test agent
./setup.sh register test-agent http://localhost:9999

# List agents
./setup.sh list

# Unregister test agent
./setup.sh unregister test-agent
```

## Documentation

- **[CONFIGURATION.md](CONFIGURATION.md)** - Complete environment variables reference
- **[DYNAMIC_REGISTRATION.md](DYNAMIC_REGISTRATION.md)** - Registry API documentation and examples

## Use Cases

1. **Security Operations Center (SOC)**
   - Deploy specialized security agents
   - Route security queries to appropriate agents
   - Centralized threat intelligence

2. **Compliance Management**
   - Register compliance agents
   - Coordinate compliance checks
   - Unified reporting

3. **Threat Modeling & Risk Assessment**
   - Multiple threat modeling agents
   - Distributed analysis
   - Aggregated results

4. **Development & Testing**
   - Hot-swap agents during development
   - A/B test different approaches
   - No orchestrator restart needed

## Performance Tuning

### For Speed
```bash
export CYBERSECURITY_AGENT_MAX_TOKENS=300
export ORCHESTRATOR_MAX_TOKENS=1000
export CYBERSECURITY_AGENT_TIMEOUT=30
```

### For Quality
```bash
export CYBERSECURITY_AGENT_MAX_TOKENS=1000
export ORCHESTRATOR_MAX_TOKENS=4000
export CYBERSECURITY_AGENT_TEMPERATURE=0.5
```

## Requirements

- Python 3.8+
- DeepSeek API key (or OpenAI)
- pip/poetry for dependency management

## Dependencies

- `strands` - Multi-agent framework
- `strands-agents` - Agent implementations
- `fastapi` - HTTP API framework
- `uvicorn` - ASGI server
- `python-dotenv` - Environment configuration
- `aiohttp` - Async HTTP client

## License

Proprietary - CAI Cybersecurity Agent

## Support

For issues and questions:
1. Check [CONFIGURATION.md](CONFIGURATION.md) for configuration issues
2. Check [DYNAMIC_REGISTRATION.md](DYNAMIC_REGISTRATION.md) for registration issues
3. Review logs for error details

## Changelog

### v1.0.0 - Dynamic Registration Release
- ✨ Dynamic agent registration via HTTP API
- ✨ Persistent agent registry (JSON file)
- ✨ Setup script for quick start
- ✨ Comprehensive documentation
- 🔄 Backward compatible with environment variables
- 🐛 Fixed token limit issues
- 📝 Added configuration guides

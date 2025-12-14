# Docker Quick Start Guide

## One-Liner Start

```bash
docker-compose up -d && sleep 3 && curl -X POST http://localhost:8000/register -d '{"name":"cybersecurity-agent","url":"http://cybersecurity:9003"}'
```

---

## Step-by-Step Setup

### 1. Setup Environment
```bash
cp .env.example .env
# Edit .env and add: DEEPSEEK_API_KEY=your-key
```

### 2. Start Services
```bash
docker-compose up -d
```

Check status:
```bash
docker-compose ps
```

### 3. Register Agent
```bash
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "cybersecurity-agent",
    "url": "http://cybersecurity:9003"
  }'
```

### 4. Verify
```bash
# Check registry
curl http://localhost:8000/agents

# Check health
curl http://localhost:8000/health
curl http://localhost:9003/health
```

### 5. View Logs
```bash
docker-compose logs -f
docker-compose logs -f orchestrator
docker-compose logs -f cybersecurity
```

---

## Docker Compose Commands

| Command | Purpose |
|---------|---------|
| `docker-compose up -d` | Start all services |
| `docker-compose down` | Stop all services |
| `docker-compose ps` | Show running services |
| `docker-compose logs -f` | View logs |
| `docker-compose build` | Rebuild images |
| `docker-compose exec orchestrator /bin/bash` | Shell into container |

---

## Services

### Orchestrator (Port 8000)
- Registry API for agent management
- A2A client for multi-agent orchestration
- Persistent agent registry in `/data`

### Cybersecurity Agent (Port 9003)
- Security consultation tools
- Threat modeling capabilities
- Compliance assessment

---

## Network Architecture

```
Docker Host
├── cai_network (bridge)
│   ├── orchestrator:8000
│   │   └── /data (volume)
│   └── cybersecurity:9003
└── Exposed Ports
    ├── 8000 → orchestrator:8000
    └── 9003 → cybersecurity:9003
```

---

## API Endpoints

**From Host Machine:**
- Registry: `http://localhost:8000`
- Agent: `http://localhost:9003`

**From Other Containers:**
- Registry: `http://orchestrator:8000`
- Agent: `http://cybersecurity:9003`

---

## Environment Variables

```bash
# API Keys (Required)
DEEPSEEK_API_KEY=your-key

# Optional (defaults provided)
OPENAI_API_KEY=
DEEPSEEK_BASE_URL=
ORCHESTRATOR_MAX_TOKENS=2000
CYBERSECURITY_AGENT_MAX_TOKENS=600
SESSION_ID=default-session
DEBUG=false
```

---

## Troubleshooting

### Check Service Status
```bash
docker-compose ps
docker-compose exec orchestrator curl http://localhost:8000/health
docker-compose exec cybersecurity curl http://localhost:9003/health
```

### View Detailed Logs
```bash
docker-compose logs orchestrator --tail 50
docker-compose logs cybersecurity --tail 50
```

### Rebuild After Code Changes
```bash
docker-compose down
docker-compose up -d --build
```

### Clean Up
```bash
docker-compose down -v
```

---

## Full API Example

```bash
# Register agent
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"name":"sec-agent","url":"http://cybersecurity:9003"}'

# List agents
curl http://localhost:8000/agents

# Get specific agent
curl http://localhost:8000/agents/sec-agent

# Unregister agent
curl -X DELETE http://localhost:8000/unregister/sec-agent

# Health check
curl http://localhost:8000/health
```

---

## Production Notes

1. **Secrets**: Use `.env` file, never commit API keys
2. **Volumes**: Agent registry persists in `orchestrator_data`
3. **Health Checks**: Both services have health endpoints
4. **Restart Policy**: Automatic restart on failure
5. **Logging**: Use `docker-compose logs` for debugging

---

## Documentation Files

- **[DOCKER.md](DOCKER.md)** - Comprehensive Docker guide
- **[docker-compose.yml](docker-compose.yml)** - Service configuration
- **[README.md](README.md)** - Project overview
- **[CONFIGURATION.md](CONFIGURATION.md)** - Environment variables
- **[DYNAMIC_REGISTRATION.md](DYNAMIC_REGISTRATION.md)** - Registry API

---

## Next Steps

1. ✅ Copy `.env.example` → `.env`
2. ✅ Add API key to `.env`
3. ✅ Run `docker-compose up -d`
4. ✅ Register agent via API
5. ✅ Query orchestrator
6. ✅ Check docs for more info

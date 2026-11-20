# MCP Servers Collection

A curated collection of Model Context Protocol (MCP) servers that enable AI assistants like Claude, Cursor, and Windsurf to interact with various services and APIs.

## Table of Contents

- [Available MCP Servers](#-available-mcp-servers)
- [All Directories](#all-directories)
- [Quick Start](#-quick-start)
- [Documentation](#-documentation)
- [Contributing](#-contributing)
- [License](#-license)
- [Author](#author)

## 🚀 Available MCP Servers

### 1. Kubectl MCP Server
**Path**: `kubectl-mcp-server/`

A comprehensive Kubernetes MCP server that enables AI assistants to interact with Kubernetes clusters through natural language.

**Features:**
- Core Kubernetes operations (pods, services, deployments, nodes)
- Helm v3 operations
- Natural language processing for kubectl commands
- Monitoring and diagnostics
- Security and RBAC management
- Multi-transport support (stdio, SSE)

**Installation:**
```bash
pip install kubectl-mcp-tool
```

**Configuration:**
```json
{
  "mcpServers": {
    "kubernetes": {
      "command": "python",
      "args": ["-m", "kubectl_mcp_tool.mcp_server"],
      "env": {
        "KUBECONFIG": "$HOME/.kube/config"
      }
    }
  }
}
```

### 2. Weather MCP Server
**Path**: `mcp-server-weathers/`

A weather information MCP server that provides real-time weather data and alerts using the National Weather Service API.

**Features:**
- Get weather forecasts by coordinates
- Fetch active weather alerts by state
- Real-time weather data from NWS API

**Setup:**
```bash
cd mcp-server-weathers
uv venv
source .venv/bin/activate
uv add "mcp[cli]" httpx
```

**Configuration:**
```json
{
  "mcpServers": {
    "weather": {
      "command": "uv",
      "args": [
        "--directory",
        "/ABSOLUTE/PATH/TO/mcp-server-weathers",
        "run",
        "weather.py"
      ]
    }
  }
}
```

### 3. Todo Automation MCP Server
**Path**: `todo-automation/`

A task management MCP server that connects to a remote task manager API for CRUD operations on todos.

**Features:**
- Create, read, update, and delete todos
- Filter by priority and completion status
- Pagination and sorting support
- Remote API integration

**Setup:**
```bash
cd todo-automation
uv venv
source .venv/bin/activate
uv install
```

**Configuration:**
```json
{
  "mcpServers": {
    "todo": {
      "command": "uv",
      "args": [
        "--directory",
        "/ABSOLUTE/PATH/TO/todo-automation",
        "run",
        "todo-automation.py"
      ]
    }
  }
}
```

### 4. Local SQL Client MCP Server
**Path**: `mcp-local-sql-client/`

A local SQLite database MCP server for managing people data with SQL operations.

**Features:**
- SQLite database operations
- Add and read people data
- Custom SQL query support
- Local data persistence

**Setup:**
```bash
cd mcp-local-sql-client
python -m venv myenv
source myenv/bin/activate
pip install -r requirements.txt
```

**Configuration:**
```json
{
  "mcpServers": {
    "sqlite": {
      "command": "python",
      "args": [
        "/ABSOLUTE/PATH/TO/mcp-local-sql-client/server.py",
        "--server_type=stdio"
      ]
    }
  }
}
```

## All Directories

The repo also holds numbered, step-by-step examples. Descriptions come from each directory's own README or file names; see the linked folder for details.

| Directory | What it contains |
|-----------|------------------|
| [3-simple-server-setup](./3-simple-server-setup/) | Simple MCP server with the Python SDK, plus stdio, SSE and streamable-HTTP clients |
| [4-geminiai-integration](./4-geminiai-integration/) | Server and client examples for Gemini integration (has `.env.example`) |
| [4.1-openai-integration](./4.1-openai-integration/) | Server and client examples for OpenAI integration (has `.env.example`) |
| [5-PP-data](./5-PP-data/) | MCP server with Docker (simple calculator tool) |
| [5.1-PP-data](./5.1-PP-data/), [5.2-PP-data](./5.2-PP-data/), [5.3-PP-data](./5.3-PP-data/) | MCP server for API integration (OpenAPI based) |
| [5.2-PP-data-fastapi-UI](./5.2-PP-data-fastapi-UI/) | FastAPI UI variant with Dockerfile, k8s and monitoring folders |
| [6.0-bedrock](./6.0-bedrock/), [6.01-open-api](./6.01-open-api/) | Agent examples (6.01 uses `strands-agents`) |
| [6.02-A2A-MCP-server](./6.02-A2A-MCP-server/) | Multi-agent system using A2A and MCP (math, research, orchestrator agents) |
| [6.03-Agent-core-agentRuntime](./6.03-Agent-core-agentRuntime/) | Agent runtime app with Dockerfile, k8s and Lambda functions (no README; TODO) |
| [7.0.1-cai-cybersecurity-agent](./7.0.1-cai-cybersecurity-agent/) | CAI cybersecurity multi-agent orchestration system |
| [7.02-CAI-JOBS](./7.02-CAI-JOBS/) | CAI jobs/session manager app with Docker and k8s files |
| [google-mcp-server](./google-mcp-server/) | Google OAuth MCP server with FastMCP |
| [mcp-client-server-chat](./mcp-client-server-chat/) | FastMCP server and chat client |
| [mail](./mail/) | Mail MCP server scripts (no README; TODO) |

`kubectl-mcp-server/` appears to be a copy of the third-party project https://github.com/rohitg00/kubectl-mcp-server (MIT, Copyright (c) 2024 Rohit Ghumare; see its own `LICENSE`).

## Configuration and secrets

Several examples ship a `.env.example`. Copy it to `.env`, fill in your own keys locally, and never commit real values.

## 🔧 Quick Start

1. **Choose an MCP server** from the list above
2. **Install dependencies** following the setup instructions
3. **Configure your AI assistant** with the provided JSON configuration
4. **Start using** the MCP server through your AI assistant

## 📖 Documentation

Each MCP server includes its own detailed documentation:

- [Kubectl MCP Server Documentation](./kubectl-mcp-server/README.md)
- [Weather MCP Server Documentation](./mcp-server-weathers/README.md)
- [Todo Automation Documentation](./todo-automation/README.md)
- [SQL Client Documentation](./mcp-local-sql-client/README.md)

## 🤝 Contributing

Feel free to contribute by:
- Adding new MCP servers
- Improving existing servers
- Fixing bugs or adding features
- Updating documentation

## 📝 License

No top-level license has been declared yet (TODO). `kubectl-mcp-server/` is third-party code under its own MIT license (see `kubectl-mcp-server/LICENSE`). Check individual directories for other licensing information.

## Author

Umesh Khatiwada - [@umesh-khatiwada](https://github.com/umesh-khatiwada)

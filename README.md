# MCP Servers Collection

A curated collection of Model Context Protocol (MCP) servers that enable AI assistants like Claude, Cursor, and Windsurf to interact with various services and APIs.

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

Each MCP server may have its own license. Please check individual project directories for specific licensing information.

# MCP Server for API Integration

## Setup

Install dependencies:

```bash
uv add mcp[cli]>=1.10.1
uv add openai>=1.75.0
uv add python-dotenv
uv add ipykernel
uv add httpx
uv add fastmcp
```

## Environment Variables

Create a `.env` file with:

```bash
GOOGLE_API_KEY=your_google_api_key_here
```


fastmcp run server.py --http 8051


## Running the Servers

1. Knowledge Base Server:
```bash
python server.py
```

2. API Server (Computesphere):
```bash
python server_2.py
```

3. Client (connects to both servers):
```bash
python client.py
```

## Available Tools

### From Knowledge Base Server:
- `get_knowledge_base`: Retrieve company knowledge base

### From API Server:
- `get_user_projects`: List all projects with filtering
- `get_project`: Get specific project details
- `list_accounts`: List accounts
- `get_account`: Get specific account details
- `list_services`: List services for a project
- `get_service`: Get specific service details
- `list_environments`: List environments for a project
- `get_environment`: Get specific environment details
- `get_deployment`: Get specific deployment details
- `get_spherestor`: List storage for an environment

## Usage

Once running, you can ask questions like:
- "get me project list"
- "show me account information"
- "what services are available for project X?"
- "what is our vacation policy?"

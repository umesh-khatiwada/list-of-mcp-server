# CAI Cybersecurity Agent Configuration Guide

## Overview

The CAI Cybersecurity Agent uses a flexible configuration system based on environment variables and Python dataclasses. All hardcoded values have been externalized, allowing you to configure the agent without modifying code.

## Configuration Structure

### Cybersecurity Agent (`cybersecurity-agent/config.py`)

Manages configuration for the cybersecurity A2A server:

```python
# Model Configuration
ModelConfig:
  - model_id: Model to use (default: "deepseek-chat")
  - api_key: API key for the model
  - base_url: API base URL
  - timeout: Request timeout in seconds (default: 60)
  - max_tokens: Max tokens per response (default: 600)
  - temperature: Response creativity (default: 0.2)

# Server Configuration
ServerConfig:
  - host: Bind host (default: "127.0.0.1")
  - port: Bind port (default: 9003)
  - public_url: Public URL for discovery (optional)
  - version: Agent version (default: "0.1.0")

# Agent Configuration
AgentConfig:
  - name: Agent name (default: "cai-cybersecurity-agent")
  - description: Agent description
  - system_prompt: Custom system prompt (optional)
```

### Orchestrator Agent (`orchestrator-agent/config.py`)

Manages configuration for the orchestrator:

```python
# Model Configuration
ModelConfig:
  - model_id: Model to use (default: "deepseek-chat")
  - api_key: API key for the model
  - base_url: API base URL
  - timeout: Request timeout in seconds (default: 60)
  - max_tokens: Max tokens per response (default: 2000)
  - temperature: Response creativity (default: 0.7)

# Agent Configuration
AgentConfig:
  - urls: List of A2A agent URLs to discover
  - cybersecurity_agent_url: URL to cybersecurity agent
  - session_id: Session ID for memory tracking
  - enable_memory: Enable conversation memory (default: false)
```

## Environment Variables

### Model Configuration

```bash
# Model selection
CAI_MODEL=deepseek-chat              # Model ID to use

# API Keys
DEEPSEEK_API_KEY=...                 # Required for DeepSeek
OPENAI_API_KEY=...                   # Fallback for API key

# API URLs
DEEPSEEK_BASE_URL=...                # DeepSeek API URL
OPENAI_BASE_URL=...                  # OpenAI API URL (fallback)

# Model parameters
CYBERSECURITY_AGENT_TIMEOUT=60        # Timeout for cybersecurity agent
ORCHESTRATOR_DEEPSEEK_TIMEOUT=60      # Timeout for orchestrator
CYBERSECURITY_AGENT_MAX_TOKENS=600    # Max tokens for cybersecurity agent
ORCHESTRATOR_MAX_TOKENS=2000          # Max tokens for orchestrator
CYBERSECURITY_AGENT_TEMPERATURE=0.2   # Temperature for cybersecurity agent
ORCHESTRATOR_TEMPERATURE=0.7          # Temperature for orchestrator
```

### Cybersecurity Agent Server

```bash
CYBERSECURITY_AGENT_HOST=127.0.0.1    # Server host
CYBERSECURITY_AGENT_PORT=9003         # Server port
CYBERSECURITY_AGENT_PUBLIC_URL=       # Public URL (optional)
CYBERSECURITY_AGENT_VERSION=0.1.0     # Agent version
```

### Orchestrator Agent

```bash
ORCHESTRATOR_AGENT_URLS=              # Comma-separated agent URLs
CYBERSECURITY_AGENT_URL=              # Cybersecurity agent URL
ORCHESTRATOR_ENABLE_MEMORY=false      # Enable memory tracking
SESSION_ID=default-session            # Session ID
```

### Agent Settings

```bash
AGENT_NAME=cai-cybersecurity-agent                    # Agent name
AGENT_DESCRIPTION=CAI cybersecurity specialist...     # Agent description
AGENT_SYSTEM_PROMPT=                                  # Custom system prompt (optional)
```

### Logging

```bash
DEBUG=false                            # Debug mode
```

## Quick Start

### 1. Copy the example configuration

```bash
cp .env.example .env
```

### 2. Edit `.env` with your values

```bash
# Set your API key
DEEPSEEK_API_KEY=your-actual-key

# Configure agent URLs (if using multiple agents)
ORCHESTRATOR_AGENT_URLS=http://127.0.0.1:9003
```

### 3. Run the agents

```bash
# Terminal 1: Cybersecurity Agent
python cybersecurity-agent/server.py

# Terminal 2: Orchestrator Agent
python orchestrator-agent/orchestrator.py
```

## Using Custom System Prompts

You can override the default system prompt by setting `AGENT_SYSTEM_PROMPT`:

```bash
export AGENT_SYSTEM_PROMPT="You are a specialized AI security consultant..."
```

Or in your `.env` file:

```
AGENT_SYSTEM_PROMPT=You are a specialized AI security consultant...
```

## API Key Configuration

The system looks for API keys in this order:

1. **DeepSeek**: First tries `DEEPSEEK_API_KEY`, then `OPENAI_API_KEY`
2. **Base URLs**: First tries `DEEPSEEK_BASE_URL`, then `OPENAI_BASE_URL`

This allows you to use the same OpenAI API key for both DeepSeek and OpenAI models, as long as they share the same base URL.

## Multi-Agent Discovery

### For the Orchestrator

The orchestrator discovers available agents through two configuration options:

```bash
# Option 1: Explicit list
ORCHESTRATOR_AGENT_URLS=http://agent1:9003,http://agent2:9004,http://agent3:9005

# Option 2: Specific cybersecurity agent
CYBERSECURITY_AGENT_URL=http://127.0.0.1:9003

# Option 3: Both (they will be merged and deduplicated)
ORCHESTRATOR_AGENT_URLS=http://agent1:9003
CYBERSECURITY_AGENT_URL=http://127.0.0.1:9003
```

## Performance Tuning

### Reduce Response Time

```bash
# Lower max tokens for faster responses
CYBERSECURITY_AGENT_MAX_TOKENS=300
ORCHESTRATOR_MAX_TOKENS=1000

# Lower timeout for faster failure detection
CYBERSECURITY_AGENT_TIMEOUT=30
ORCHESTRATOR_DEEPSEEK_TIMEOUT=30
```

### Improve Response Quality

```bash
# Increase max tokens for more detailed responses
CYBERSECURITY_AGENT_MAX_TOKENS=1000
ORCHESTRATOR_MAX_TOKENS=4000

# Increase temperature for more creative responses
CYBERSECURITY_AGENT_TEMPERATURE=0.5
ORCHESTRATOR_TEMPERATURE=1.0
```

## Configuration Validation

The configuration system validates:

- **API Key**: Ensures at least one API key (DeepSeek or OpenAI) is set
- **Model ID**: Validates model_id is provided
- **Port Numbers**: Converts port strings to integers
- **Timeouts**: Converts timeout strings to floats
- **Temperature**: Converts temperature strings to floats

If validation fails, helpful error messages guide you to fix the configuration.

## Code Integration

### Accessing Configuration

In any agent file:

```python
from config import get_config

config = get_config()
api_key = config.model.api_key
server_port = config.server.port
```

### Using Configuration in Functions

```python
def build_agent():
    return Agent(
        name=config.agent.name,
        model_id=config.model.model_id,
        # ... other config values
    )
```

## Environment Variable Precedence

When multiple environment variables could provide a value, the precedence is:

1. **Specific variable** (e.g., `DEEPSEEK_API_KEY`)
2. **Fallback variable** (e.g., `OPENAI_API_KEY`)
3. **Default value** (hard-coded in config class)

Example for API key:

```python
api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY") or default
```

## Troubleshooting

### "Set DEEPSEEK_API_KEY or OPENAI_API_KEY"

**Problem**: No API key configured

**Solution**: 
```bash
export DEEPSEEK_API_KEY=your-key
# or
export OPENAI_API_KEY=your-key
```

### Agent not discovered by orchestrator

**Problem**: Orchestrator can't reach cybersecurity agent

**Solution**: 
```bash
# Check that agent is running
# Check that CYBERSECURITY_AGENT_URL or ORCHESTRATOR_AGENT_URLS is correct
export CYBERSECURITY_AGENT_URL=http://127.0.0.1:9003
```

### Responses timing out

**Problem**: Requests timeout

**Solution**: Increase timeout values
```bash
export CYBERSECURITY_AGENT_TIMEOUT=120
export ORCHESTRATOR_DEEPSEEK_TIMEOUT=120
```

## Files Reference

- **`cybersecurity-agent/config.py`**: Cybersecurity agent configuration
- **`orchestrator-agent/config.py`**: Orchestrator configuration
- **`cybersecurity-agent/server.py`**: Uses `config.get_config()`
- **`orchestrator-agent/orchestrator.py`**: Uses `config.get_config()`
- **`.env.example`**: Template with all available variables
- **`.env`**: Your local configuration (not in git)

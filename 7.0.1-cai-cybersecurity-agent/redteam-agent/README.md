# Red Team Agent - Local Setup & Running Guide

## Overview

The Red Team Agent is a security-focused agent designed for:
- CTF (Capture The Flag) challenges
- Penetration testing
- Security assessments
- Multi-agent security operations

## Quick Start

### 1. Install Dependencies
```bash
cd redteam-agent
pip install -r requirements.txt
```

### 2. Setup Environment
```bash
# Copy environment template
cp ../.env.example .env

# Edit .env with your settings
# At minimum, add:
# DEEPSEEK_API_KEY=your-key
# or
# OPENAI_API_KEY=your-key
```

### 3. Run the Agent
```bash
# Option 1: Using the run script
python run.py

# Option 2: Direct execution
python -m redtem_agent

# Option 3: Using asyncio directly
python -c "import asyncio; from redtem_agent import main; asyncio.run(main())"
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CAI_MODEL` | `deepseek-chat` | Model to use |
| `DEEPSEEK_API_KEY` | - | DeepSeek API key (required) |
| `OPENAI_API_KEY` | - | OpenAI API key (fallback) |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.ai/v1/` | DeepSeek API URL |
| `OPENAI_BASE_URL` | `https://api.openai.com/v1/` | OpenAI API URL |
| `REDTEAM_AGENT_TIMEOUT` | `60` | Request timeout in seconds |
| `REDTEAM_AGENT_MAX_TOKENS` | `1000` | Max tokens per response |
| `REDTEAM_AGENT_TEMPERATURE` | `0.7` | Response creativity (0-1) |
| `AGENT_NAME` | `redteam-agent` | Agent name |
| `AGENT_DESCRIPTION` | `Red team security agent...` | Agent description |
| `AGENT_SYSTEM_PROMPT` | `You are a cybersecurity expert...` | Custom system prompt |

### Example .env File
```bash
# API Configuration
CAI_MODEL=deepseek-chat
DEEPSEEK_API_KEY=sk-your-key-here
DEEPSEEK_BASE_URL=https://api.deepseek.ai/v1/

# Agent Settings
REDTEAM_AGENT_TIMEOUT=60
REDTEAM_AGENT_MAX_TOKENS=1000
REDTEAM_AGENT_TEMPERATURE=0.7

# Custom Agent Configuration
AGENT_NAME=redteam-agent
AGENT_SYSTEM_PROMPT=You are a cybersecurity expert specializing in red team operations and CTF challenges
```

## Running Modes

### Mode 1: Normal Execution
```bash
python run.py
```
- Executes agent tasks sequentially
- Waits for full responses
- Good for structured testing

### Mode 2: Streaming
```python
# Inside main_streamed() in redtem_agent.py
# Real-time event streaming
# Good for monitoring and debugging
```

### Mode 3: Custom Prompts
Modify the prompt in `redtem_agent.py`:
```python
async def main():
    result = await Runner.run(ctf_agent, "Your custom security task here")
    print(result.final_output)
```

## File Structure

```
redteam-agent/
├── redtem_agent.py      # Main agent implementation
├── config.py            # Configuration management
├── run.py               # Simple runner script
├── requirements.txt     # Dependencies
├── README.md            # This file
└── .env                 # Environment variables (not in git)
```

## Available Tools

### execute_cli_command
Execute shell commands for security testing:
```python
@function_tool
def execute_cli_command(command: str) -> str:
    return run_command(command)
```

**Examples:**
- `ls -la` - List files
- `nmap -p 80,443 target` - Network scanning
- `curl http://target.com` - HTTP requests
- `python exploit.py` - Run custom scripts

## Development

### Adding New Tools

```python
from cai.sdk.agents import function_tool

@function_tool
def my_security_tool(param1: str) -> str:
    """Tool description for the agent."""
    # Implementation
    return result

# Add to agent:
ctf_agent = Agent(
    tools=[
        execute_cli_command,
        my_security_tool,  # Add here
    ],
    # ... other config
)
```

### Testing the Agent

```bash
# Test with custom prompt
python -c "
import asyncio
from redtem_agent import ctf_agent, Runner

async def test():
    result = await Runner.run(ctf_agent, 'Your test prompt')
    print(result.final_output)

asyncio.run(test())
"
```

## Troubleshooting

### API Key Issues
```bash
# Check environment variable is set
echo $DEEPSEEK_API_KEY

# Set it temporarily
export DEEPSEEK_API_KEY=sk-your-key
python run.py
```

### Import Errors
```bash
# Ensure all dependencies are installed
pip install -r requirements.txt

# Verify CAI framework is installed
python -c "import cai; print(cai.__version__)"
```

### Connection Issues
```bash
# Test API connection
curl -X POST https://api.deepseek.ai/v1/chat/completions \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"test"}]}'
```

### Timeout Issues
```bash
# Increase timeout
export REDTEAM_AGENT_TIMEOUT=120
python run.py
```

## Performance Tuning

### For Speed
```bash
export REDTEAM_AGENT_MAX_TOKENS=500
export REDTEAM_AGENT_TIMEOUT=30
python run.py
```

### For Quality
```bash
export REDTEAM_AGENT_MAX_TOKENS=2000
export REDTEAM_AGENT_TEMPERATURE=0.5
python run.py
```

## Security Considerations

⚠️ **Important**: Be careful with:
- `execute_cli_command` - Only run trusted commands
- Network scanning - Ensure you have permission
- Credential handling - Never hardcode credentials
- Command injection - Validate all inputs

## Use Cases

1. **CTF Competitions**
   - Automated challenge solving
   - Vulnerability discovery
   - Exploitation scripting

2. **Penetration Testing**
   - Reconnaissance
   - Vulnerability assessment
   - Reporting

3. **Security Research**
   - Proof-of-concept development
   - Vulnerability analysis
   - Threat modeling

4. **Learning**
   - Security concepts
   - CAI framework usage
   - Multi-agent systems

## Integration with Other Agents

Use with orchestrator for multi-agent security operations:

```bash
# Terminal 1: Start orchestrator
cd ../orchestrator-agent
python orchestrator.py

# Terminal 2: Register red team agent
curl -X POST http://localhost:8000/register \
  -d '{"name":"redteam-agent","url":"http://redteam:9005"}'

# Terminal 3: Start red team agent server
python server.py  # (if A2A server implemented)
```

## Advanced Usage

### Custom System Prompt
```bash
export AGENT_SYSTEM_PROMPT="You are a specialized vulnerability researcher..."
python run.py
```

### Batch Testing
```bash
# Create test_prompts.txt with multiple prompts
for prompt in $(cat test_prompts.txt); do
    echo "Testing: $prompt"
    python -c "
import asyncio
from redtem_agent import ctf_agent, Runner
asyncio.run(Runner.run(ctf_agent, '$prompt'))
"
done
```

## Logging

Enable detailed logging:
```bash
# Set logging level
export LOG_LEVEL=DEBUG
python run.py
```

View logs:
```bash
# From stderr
python run.py 2>&1 | grep -i "error\|warning"

# Pipe to file
python run.py >> redteam.log 2>&1
```

## Support & Documentation

- [../README.md](../README.md) - Main project documentation
- [../CONFIGURATION.md](../CONFIGURATION.md) - Configuration reference
- [../DYNAMIC_REGISTRATION.md](../DYNAMIC_REGISTRATION.md) - Agent registration

## License

Proprietary - CAI Red Team Agent

## Version

Red Team Agent v0.1.0

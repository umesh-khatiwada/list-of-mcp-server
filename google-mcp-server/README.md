# Google OAuth MCP Server

A Model Context Protocol (MCP) server that demonstrates Google OAuth authentication with FastMCP.

## Features

- 🔐 Google OAuth 2.0 authentication
- 🔌 MCP protocol support for integration with AI assistants
- 🌐 HTTP mode for testing and development
- 🛡️ Graceful shutdown handling
- 📝 Comprehensive logging

## Quick Start

### 1. Installation

```bash
# Clone or navigate to the project directory
cd google-mcp-server

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .
```

### 2. Configuration

Copy the environment template and configure your Google OAuth credentials:

```bash
cp .env.example .env
```

Edit `.env` and add your Google OAuth credentials:

```bash
export FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID=your_client_id_here
export FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_SECRET=your_client_secret_here
```

### 3. Get Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/apis/credentials)
2. Create a new OAuth 2.0 Client ID
3. Set the authorized redirect URI to: `http://localhost:8000/auth/callback`
4. Copy the Client ID and Client Secret to your `.env` file

### 4. Running the Server

#### As MCP Server (for AI assistants)

```bash
# Load environment variables
source .env

# Start MCP server
python server.py
```

#### As HTTP Server (for testing)

```bash
# Load environment variables  
source .env

# Start HTTP server on port 8000
python server.py --http

# Or specify a different port
python server.py --http --port 9000
```

#### Using the Launcher (Recommended)

```bash
# The launcher handles environment setup automatically
python launch.py
```

## MCP Integration

### For Cline/Claude Desktop

Add this configuration to your MCP settings:

```json
{
  "mcpServers": {
    "google-oauth": {
      "command": "python",
      "args": ["/path/to/your/google-mcp-server/launch.py"],
      "env": {
        "FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID": "your_client_id",
        "FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_SECRET": "your_client_secret"
      }
    }
  }
}
```

Or use the provided configuration file:

```bash
# Update the path in mcp_config.json and copy to your MCP settings
cat mcp_config.json
```

## Available Tools

The server provides the following MCP tools:

- `echo` - Echo a message back
- `get_google_auth_status` - Check OAuth configuration status
- `get_user_info` - Get authenticated user information
- `health_check` - Check server health status  
- `list_tools` - List all available tools

## Troubleshooting

### Common Issues

1. **MCP Request Timeout**
   - Ensure the server is running with `stdio` transport (default)
   - Check that the path in your MCP configuration is correct
   - Verify Python dependencies are installed

2. **OAuth Not Working**
   - Check that your `.env` file has the correct credentials
   - Verify the redirect URI is set to `http://localhost:8000/auth/callback`
   - Ensure your Google OAuth application is configured correctly

3. **Import Errors**
   - Make sure you're in the virtual environment: `source .venv/bin/activate`
   - Install dependencies: `pip install -e .`

### Testing the Server

```bash
# Test basic functionality
python test_server.py

# Test HTTP endpoint (if running in HTTP mode)
curl http://localhost:8000
```

### Logs

The server provides detailed logging. Check the console output for:
- Server startup/shutdown messages
- Tool execution logs
- Authentication status
- Error messages

## Development

### Running Without OAuth

The server can run without OAuth credentials for development:

```bash
# Just start the server - it will warn about missing credentials but still work
python server.py
```

### Adding New Tools

Add new tools by decorating functions with `@mcp.tool`:

```python
@mcp.tool
def my_new_tool(param: str) -> str:
    """Description of what this tool does."""
    return f"Result: {param}"
```

## Security Notes

- Keep your OAuth credentials secure and never commit them to version control
- The `.env` file is gitignored by default
- In production, consider using environment variables or secure secret management
- The server includes CORS and other security headers when running in HTTP mode

## License

This project is provided as an example for educational purposes.

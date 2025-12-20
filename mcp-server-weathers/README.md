# Weather MCP Server

A Model Context Protocol (MCP) server that provides real-time weather information and alerts using the National Weather Service (NWS) API. This server enables AI assistants to fetch weather forecasts and active weather alerts for locations in the United States.

## Features

- **Weather Forecasts**: Get detailed weather forecasts for any coordinates in the US
- **Weather Alerts**: Fetch active weather alerts by state
- **NWS API Integration**: Uses the official National Weather Service API
- **Real-time Data**: Access to current weather conditions and forecasts
- **Detailed Information**: Temperature, wind, and comprehensive weather descriptions

## Prerequisites

- Python 3.11+
- uv package manager
- Internet connection for API access

## Installation

### Using uv (Recommended)

```bash
# Install uv if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Navigate to the project directory
cd mcp-server-weathers

# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv add "mcp[cli]" httpx
```

### Manual Installation

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install httpx "mcp[cli]"
```

## Configuration

### AI Assistant Configuration

Add the following to your AI assistant's MCP configuration:

#### Claude Desktop
Add to `~/Library/Application\ Support/Claude/claude_desktop_config.json`:
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

#### Cursor AI
Add to `~/.cursor/mcp.json`:
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

#### Windsurf
Add to `~/.config/windsurf/mcp.json`:
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

> **Note**: Replace `/ABSOLUTE/PATH/TO/mcp-server-weathers` with the actual absolute path to your mcp-server-weathers directory.

## Usage

Once configured, you can interact with the weather service through your AI assistant using natural language:

### Getting Weather Forecasts
- "What's the weather forecast for New York City?" (You'll need to provide coordinates)
- "Get me the weather forecast for latitude 40.7128, longitude -74.0060"
- "Show me the 5-day forecast for San Francisco"

### Getting Weather Alerts
- "Are there any weather alerts for California?"
- "Check weather alerts for Texas"
- "Show me active weather alerts for NY"

## API Reference

The MCP server provides the following tools:

### get_forecast
Gets weather forecast for specific coordinates.

**Parameters:**
- `latitude` (float): Latitude of the location (required)
- `longitude` (float): Longitude of the location (required)

**Returns:**
- Detailed weather forecast for the next 5 periods
- Temperature, wind information, and detailed descriptions

### get_alerts
Gets active weather alerts for a US state.

**Parameters:**
- `state` (str): Two-letter US state code (e.g., CA, NY, TX) (required)

**Returns:**
- List of active weather alerts including:
  - Event type
  - Affected area
  - Severity level
  - Description and instructions

## Testing

Test the server directly:

```bash
# Test the module import
uv run python -c "import weather; print('Weather module loaded successfully')"

# Run the server directly
uv run weather.py

# Test with specific coordinates (example for New York City)
# This would be done through your AI assistant once configured
```

## Example Interactions

### Weather Forecast Example
```
User: "Get me the weather forecast for New York City"
Assistant: "I'll need the coordinates for New York City. The latitude is 40.7128 and longitude is -74.0060."

Response:
Tonight:
Temperature: 45°F
Wind: 10 mph NW
Forecast: Partly cloudy with temperatures falling to around 45 degrees.

Tomorrow:
Temperature: 62°F
Wind: 8 mph SW
Forecast: Sunny skies with high temperatures reaching 62 degrees.
...
```

### Weather Alerts Example
```
User: "Are there any weather alerts for California?"

Response:
Event: Winter Storm Warning
Area: Sierra Nevada Mountains
Severity: Moderate
Description: Heavy snow expected above 3000 feet elevation.
Instructions: Avoid unnecessary travel in mountainous areas.
```

## Data Source

This server uses the [National Weather Service API](https://www.weather.gov/documentation/services-web-api), which provides:
- Free access to US weather data
- Real-time weather information
- Official government weather alerts
- No API key required

## Limitations

- **US Only**: The NWS API only covers United States territories
- **Coordinates Required**: Weather forecasts require precise latitude/longitude coordinates
- **Rate Limits**: The NWS API has rate limiting (usually generous for personal use)

## Troubleshooting

### Common Issues

1. **"Unable to fetch forecast data"**
   - Verify coordinates are within US boundaries
   - Check internet connection
   - Ensure coordinates are valid decimal degrees

2. **Module not found error**
   - Ensure you're in the correct directory
   - Verify virtual environment is activated
   - Check that dependencies are installed

3. **No alerts found**
   - Use valid two-letter state codes (CA, NY, TX, etc.)
   - Some states may not have active alerts

## License

This project is part of the MCP Servers Collection. Please refer to the main repository for licensing information.

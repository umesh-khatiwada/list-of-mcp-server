# Local SQL Client MCP Server

A Model Context Protocol (MCP) server that provides local SQLite database operations for managing people data. This server enables AI assistants to interact with a local SQLite database using SQL queries.

## Features

- **SQLite Database**: Local database for persistent data storage
- **People Management**: Add and read people data with name, age, and profession
- **Custom SQL Queries**: Support for custom SELECT and INSERT queries
- **Auto-initialization**: Database and tables are created automatically
- **Multiple Transport Types**: Support for both stdio and SSE transport

## Prerequisites

- Python 3.7+
- SQLite (usually included with Python)

## Installation

### Using pip

```bash
# Navigate to the project directory
cd mcp-local-sql-client

# Create virtual environment
python -m venv myenv

# Activate virtual environment
source myenv/bin/activate  # On Windows: myenv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Manual Installation

```bash
# Install required packages
pip install mcp sqlite3
```

## Database Schema

The server uses a SQLite database (`demo.db`) with the following schema:

```sql
CREATE TABLE people (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    age INTEGER NOT NULL,
    profession TEXT NOT NULL
)
```

## Configuration

### AI Assistant Configuration

Add the following to your AI assistant's MCP configuration:

#### Claude Desktop
Add to `~/Library/Application\ Support/Claude/claude_desktop_config.json`:
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

#### Cursor AI
Add to `~/.cursor/mcp.json`:
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

#### For SSE Transport (HTTP-based)
```json
{
  "mcpServers": {
    "sqlite": {
      "command": "python",
      "args": [
        "/ABSOLUTE/PATH/TO/mcp-local-sql-client/server.py",
        "--server_type=sse"
      ]
    }
  }
}
```

> **Note**: Replace `/ABSOLUTE/PATH/TO/mcp-local-sql-client` with the actual absolute path to your mcp-local-sql-client directory.

## Usage

Once configured, you can interact with the SQLite database through your AI assistant using natural language:

### Adding Data
- "Add a new person named John Doe, age 30, profession Engineer"
- "Insert Alice Smith, 25 years old, works as a Developer"
- "Add someone named Bob Johnson who is 35 and works as a Manager"

### Reading Data
- "Show me all people in the database"
- "List everyone who is older than 25"
- "Get all developers from the database"
- "Show me people sorted by age"

## API Reference

The MCP server provides the following tools:

### add_data
Adds new data to the people table using a SQL INSERT query.

**Parameters:**
- `query` (str): SQL INSERT query (required)

**Example:**
```sql
INSERT INTO people (name, age, profession)
VALUES ('John Doe', 30, 'Engineer')
```

**Returns:**
- `bool`: True if data was added successfully, False otherwise

### read_data
Reads data from the people table using a SQL SELECT query.

**Parameters:**
- `query` (str): SQL SELECT query (optional, defaults to "SELECT * FROM people")

**Example Queries:**
```sql
-- Get all records
SELECT * FROM people

-- Get specific columns
SELECT name, age FROM people WHERE age > 25

-- Sort by age
SELECT * FROM people ORDER BY age DESC

-- Filter by profession
SELECT * FROM people WHERE profession = 'Engineer'
```

**Returns:**
- `list`: List of tuples containing query results

## Running the Server

### Command Line Options

```bash
# Run with stdio transport (default)
python server.py --server_type=stdio

# Run with SSE transport (HTTP-based)
python server.py --server_type=sse
```

### Direct Testing

```bash
# Test the server directly
python server.py

# For SSE mode, the server will start on port 8000
# You can access it via HTTP at http://localhost:8000
```

## Example Interactions

### Adding People
```
User: "Add a new person to the database: Sarah Wilson, 28 years old, Teacher"

The system will execute:
INSERT INTO people (name, age, profession)
VALUES ('Sarah Wilson', 28, 'Teacher')

Response: "Data added successfully"
```

### Querying Data
```
User: "Show me all teachers in the database"

The system will execute:
SELECT * FROM people WHERE profession = 'Teacher'

Response: [(1, 'Sarah Wilson', 28, 'Teacher')]
```

## Database File

The SQLite database file (`demo.db`) is created automatically in the project directory. This file persists data between server restarts.

### Database Location
- Default: `./demo.db` (in the project directory)
- The database file is created automatically if it doesn't exist
- Data persists between server restarts

## Troubleshooting

### Common Issues

1. **Database locked error**
   - Ensure no other process is accessing the database
   - Restart the server if connections aren't properly closed

2. **SQL syntax errors**
   - Verify SQL query syntax
   - Ensure table and column names are correct
   - Use proper SQL escaping for string values

3. **Module not found error**
   - Ensure virtual environment is activated
   - Check that dependencies are installed correctly

4. **Permission denied**
   - Check write permissions in the project directory
   - Ensure the database file can be created/modified

## Security Considerations

- This server is designed for local development and testing
- SQL injection protection is minimal - validate queries in production use
- The database file is stored locally and accessible to the Python process
- Consider implementing proper authentication for production deployments

## License

This project is part of the MCP Servers Collection. Please refer to the main repository for licensing information.

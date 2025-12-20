# Todo Automation MCP Server

A Model Context Protocol (MCP) server for task management that enables AI assistants to interact with a remote task manager API for CRUD operations on todos.

## Features

- **Create Todos**: Add new tasks with title, description, priority, and due dates
- **Read Todos**: Fetch todos with filtering, pagination, and sorting options
- **Update Todos**: Modify existing todos including completion status
- **Delete Todos**: Remove todos by ID
- **Advanced Filtering**: Filter by priority, completion status
- **Pagination Support**: Handle large todo lists efficiently
- **Remote API Integration**: Connect to external task management systems

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
cd todo-automation

# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv install
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

#### Cursor AI
Add to `~/.cursor/mcp.json`:
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

#### Windsurf
Add to `~/.config/windsurf/mcp.json`:
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

> **Note**: Replace `/ABSOLUTE/PATH/TO/todo-automation` with the actual absolute path to your todo-automation directory.

## Usage

Once configured, you can interact with the todo system through your AI assistant using natural language:

### Creating Todos
- "Create a new todo to finish the project report with high priority"
- "Add a task to buy groceries due tomorrow"
- "Create a medium priority todo for team meeting preparation"

### Reading Todos
- "Show me all my todos"
- "List high priority tasks"
- "Get completed todos from last week"
- "Show me the first 5 todos sorted by creation date"

### Updating Todos
- "Mark todo #5 as completed"
- "Update the priority of task #3 to high"
- "Change the description of todo #7"

### Deleting Todos
- "Delete todo #12"
- "Remove the completed shopping task"

## API Reference

The MCP server provides the following tools:

### get_todos
Fetches todos with optional filtering and pagination.

**Parameters:**
- `page` (int): Page number (default: 1)
- `limit` (int): Items per page (default: 10)
- `sortBy` (str): Sort field (default: "created_at")
- `sortOrder` (str): Sort direction (default: "DESC")
- `priority` (str): Filter by priority ("low", "medium", "high")
- `completed` (bool): Filter by completion status

### post_todos
Creates a new todo.

**Parameters:**
- `title` (str): Todo title (required)
- `description` (str): Todo description (required)
- `priority` (str): Priority level (default: "medium")
- `end_date` (str): Due date in ISO format (optional)

### update_todo
Updates an existing todo.

**Parameters:**
- `task_id` (int): Todo ID (required)
- `title` (str): Updated title (required)
- `description` (str): Updated description (required)
- `priority` (str): Updated priority (default: "medium")
- `end_date` (str): Updated due date (optional)
- `completed` (bool): Completion status (default: false)

### delete_todo
Deletes a todo by ID.

**Parameters:**
- `task_id` (int): Todo ID to delete (required)

## Testing

Test the server directly:

```bash
# Test the module import
uv run python -c "import todo_automation; print('Todo automation module loaded successfully')"

# Run the server directly
uv run todo-automation.py
```

## Troubleshooting

### Common Issues

1. **Module not found error**
   - Ensure you're in the correct directory
   - Verify virtual environment is activated
   - Check that dependencies are installed

2. **API connection errors**
   - Verify internet connection
   - Check if the API endpoint is accessible
   - Ensure authentication token is valid

3. **Permission denied**
   - Check file permissions
   - Ensure the script is executable

## API Endpoint

The server connects to: `https://task-manager-api.do.umeshkhatiwada.com.np/api`

**Note**: This is a demo API. For production use, replace with your own task management API endpoint and update the authentication token in the code.

## License

This project is part of the MCP Servers Collection. Please refer to the main repository for licensing information.

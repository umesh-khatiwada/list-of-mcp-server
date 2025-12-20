from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

# from fastmcp.client.auth import OAuth

# Initialize FastMCP server
mcp = FastMCP("todo-automation")
# oauth = OAuth(mcp_url="https://fastmcp.cloud/mcp")


# Constants
NWS_API_BASE = "https://task-manager-api.do.umeshkhatiwada.com.np/api"
USER_AGENT = (
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:141.0) Gecko/20100101 Firefox/141.0"
)
AUTHORIZATION = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6NywiaWF0IjoxNzU1Njg0NjI5LCJleHAiOjE3NTYyODk0Mjl9.YtkbxQhCdXNrk3xVCOGPNmRDU_uju_xElP17Qkqz9tY"
HEADER = {"User-Agent": USER_AGENT, "Authorization": AUTHORIZATION}


@mcp.tool()
async def get_todos(
    page: int = 1,
    limit: int = 10,
    sortBy: str = "created_at",
    sortOrder: str = "DESC",
    priority: str = None,
    completed: bool = None,
) -> Any:
    """
    Fetches the list of todos from the Task Manager API with optional filtering and pagination.
    """
    params = {"page": page, "limit": limit, "sortBy": sortBy, "sortOrder": sortOrder}

    # Add optional filters if provided
    if priority is not None:
        params["priority"] = priority
    if completed is not None:
        params["completed"] = str(completed).lower()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                f"{NWS_API_BASE}/tasks", headers=HEADER, params=params
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": f"Failed to fetch todos: {str(e)}"}


@mcp.tool()
async def post_todos(
    title: str, description: str, priority: str = "medium", end_date: str = None
) -> Any:
    """
    Creates a new todo in the Task Manager API.
    """
    todo_data = {
        "title": title,
        "description": description,
        "priority": priority,
        "end_date": end_date,
        "completed": False,
    }
    # The URL for creating a new todo
    url = f"{NWS_API_BASE}/tasks"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=HEADER, json=todo_data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": f"Failed to create todo: {str(e)}"}


@mcp.tool()
async def delete_todo(task_id: int) -> Any:
    """
    Deletes a todo from the Task Manager API by ID.
    """
    url = f"{NWS_API_BASE}/tasks/{task_id}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(url, headers=HEADER)
            response.raise_for_status()
            return {"success": f"Todo with ID {task_id} deleted successfully"}
        except Exception as e:
            return {"error": f"Failed to delete todo: {str(e)}"}


@mcp.tool()
async def update_todo(
    task_id: int,
    title: str,
    description: str,
    priority: str = "medium",
    end_date: str = None,
    completed: bool = False,
) -> Any:
    """
    Updates a todo in the Task Manager API by ID.
    """
    todo_data = {
        "title": title,
        "description": description,
        "priority": priority,
        "end_date": end_date,
        "completed": completed,
    }
    url = f"{NWS_API_BASE}/tasks/{task_id}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(url, headers=HEADER, json=todo_data)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": f"Failed to update todo: {str(e)}"}


if __name__ == "__main__":
    # Initialize and run the server
    mcp.run(transport="stdio")

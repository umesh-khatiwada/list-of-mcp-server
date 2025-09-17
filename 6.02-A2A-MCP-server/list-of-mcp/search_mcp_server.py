# A toy MCP server exposing a fake search tool
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("search-mcp")

@mcp.tool()
def search(query: str) -> str:
    """Fake search that returns canned results."""
    return f"Search results for '{query}': [example result]"

mcp.run()

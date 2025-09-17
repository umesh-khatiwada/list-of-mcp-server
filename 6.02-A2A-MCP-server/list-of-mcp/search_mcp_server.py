# A toy MCP server exposing a fake search tool
from mcp.server.fastmcp import FastMCP
import requests

mcp = FastMCP("search-mcp")

@mcp.tool(name="search", description="Perform a web search")
def search(query: str) -> str:
    """Performs a real web search using DuckDuckGo Instant Answer API."""
    url = "https://api.duckduckgo.com/"
    params = {"q": query, "format": "json"}
    try:
        resp = requests.get(url, params=params)
        data = resp.json()
        answer = data.get("AbstractText") or "No direct answer found."
        return f"Search results for '{query}': {answer}"
    except Exception as e:
        return f"Error during search: {e}"

mcp.run()

# A toy MCP server exposing a fake search tool
import os
from mcp.server.fastmcp import FastMCP
import requests
from dotenv import load_dotenv

load_dotenv()

mcp = FastMCP("search-mcp")
API_URL = "https://www.searchapi.io/api/v1/search"
API_KEY = os.getenv("SEARCH_API_KEY")

@mcp.tool(name="search", description="Perform a web search using SearchAPI.io Google engine")
def search(query: str) -> str:
    params = {
        "q": query,
        "engine": "google"
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    try:
        resp = requests.get(API_URL, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        # Extract top results
        results = data.get("organic_results", [])
        if results:
            top_results = []
            for r in results[:5]:
                title = r.get("title", "No title")
                link = r.get("link", "")
                snippet = r.get("snippet", "")
                top_results.append(f"{title}\n{snippet}\n{link}")
            return f"Top search results for '{query}':\n\n" + "\n\n".join(top_results)
        else:
            return f"No results found for '{query}'."
    except requests.exceptions.Timeout:
        return "Error: Search request timed out."
    except requests.exceptions.RequestException as e:
        return f"Error during search: {e}"
    except Exception as e:
        return f"Unexpected error during search: {e}"

mcp.run()

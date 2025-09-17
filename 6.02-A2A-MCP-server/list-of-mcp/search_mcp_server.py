# A toy MCP server exposing a fake search tool
from mcp.server.fastmcp import FastMCP
import requests

mcp = FastMCP("search-mcp")

@mcp.tool(name="search", description="Perform a web search")
def search(query: str) -> str:
    url = "https://api.duckduckgo.com/"
    params = {
        "q": query,
        "format": "json",
        "no_redirect": 1,
        "no_html": 1
    }
    try:
        resp = requests.get(url, params=params)
        data = resp.json()

        # Check for direct answer
        answer = data.get("AbstractText")
        if answer:
            return f"Search results for '{query}': {answer}"

        # If no direct answer, extract related topics
        related = data.get("RelatedTopics", [])
        suggestions = []

        def extract_topics(topics):
            for topic in topics:
                # Some topics are nested in "Topics" field
                if "Topics" in topic:
                    extract_topics(topic["Topics"])
                elif "Text" in topic and "FirstURL" in topic:
                    suggestions.append(f"{topic['Text']} ({topic['FirstURL']})")
                if len(suggestions) >= 5:
                    break

        extract_topics(related)

        if suggestions:
            answer = "No direct answer found. Related topics:\n- " + "\n- ".join(suggestions[:5])
        else:
            answer = (
                "No direct answer found. "
                "Try refining your search with queries like:\n"
                "- 'cloud provider comparison'\n"
                "- 'AWS vs Azure vs Google Cloud'\n"
                "- 'cloud provider pricing 2025'\n"
                "- 'cloud provider reliability reviews'"
            )

        return f"Search results for '{query}':\n{answer}"

    except Exception as e:
        return f"Error during search: {e}"

mcp.run()

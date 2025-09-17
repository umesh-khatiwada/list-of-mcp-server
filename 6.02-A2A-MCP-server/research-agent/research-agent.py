from strands import Agent
from strands.multiagent.a2a import A2AServer
from strands.tools.mcp import MCPClient
from mcp import stdio_client, StdioServerParameters

# Connect to the local search MCP server
mcp_client = MCPClient(lambda: stdio_client(
    StdioServerParameters(command="python", args=["./list-of-mcp/search_mcp_server.py"])
))

with mcp_client:
    tools = mcp_client.list_tools_sync()
    research_agent = Agent(name="research_agent", description="A research agent that exposes search tools via MCP.", tools=tools)

    # Expose via A2A
    server = A2AServer(agent=research_agent, port=9002)
    server.serve()

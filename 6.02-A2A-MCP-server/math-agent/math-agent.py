from strands import Agent
from strands.multiagent.a2a import A2AServer
from strands.tools.mcp import MCPClient
from mcp import stdio_client, StdioServerParameters

# Connect to the local math MCP server
mcp_client = MCPClient(lambda: stdio_client(
    StdioServerParameters(command="python", args=["./list-of-mcp/math_mcp_server.py"])
))

with mcp_client:
    tools = mcp_client.list_tools_sync()
    math_agent = Agent(name="math_agent",description="A math agent that exposes math tools via MCP.", tools=tools)

    # Expose via A2A
    server = A2AServer(agent=math_agent, port=9001)
    server.serve()

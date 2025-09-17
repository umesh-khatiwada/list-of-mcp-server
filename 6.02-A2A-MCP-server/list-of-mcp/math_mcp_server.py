# A toy MCP server exposing math functions
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("math-mcp")

@mcp.tool(name="add",description="Add two numbers")
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b

@mcp.tool(name="multiply",description="Multiply two numbers")
def multiply(a: int, b: int) -> int:
    """Multiply two numbers."""
    return a * b

mcp.run()

# A comprehensive MCP server exposing mathematical functions
import math

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("math-mcp-radian")


# Angle Conversion
@mcp.tool(name="deg_to_rad", description="Convert degrees to radians")
def deg_to_rad(degrees: float) -> float:
    """Convert degrees to radians."""
    try:
        result = math.radians(degrees)
        return result
    except Exception as e:
        return f"Error in degree to radian conversion: {e}"


@mcp.tool(name="rad_to_deg", description="Convert radians to degrees")
def rad_to_deg(radians: float) -> float:
    """Convert radians to degrees."""
    try:
        result = math.degrees(radians)
        return result
    except Exception as e:
        return f"Error in radian to degree conversion: {e}"


mcp.run()

"""
Google OAuth FastMCP Server Example
Run: python server.py
"""

import os
from fastmcp import FastMCP
from fastmcp.server.auth.providers.google import GoogleProvider
from dotenv import load_dotenv
from tools import get_user_info, is_logged_in, get_login_url, logout, get_user_email

# Load environment variables from .env file
load_dotenv()

# Google OAuth setup
auth = GoogleProvider(
    client_id=os.getenv("FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_ID") or "",
    client_secret=os.getenv("FASTMCP_SERVER_AUTH_GOOGLE_CLIENT_SECRET") or "",
    base_url="http://localhost:8000",
)

# FastMCP server
mcp = FastMCP("Google OAuth Example Server", auth=auth)

# Register tools
mcp.tool(get_user_info)
mcp.tool(is_logged_in)
mcp.tool(get_login_url)
mcp.tool(logout)
mcp.tool(get_user_email)

@mcp.tool
def echo(message: str) -> str:
    """Echo the provided message."""
    return message

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)

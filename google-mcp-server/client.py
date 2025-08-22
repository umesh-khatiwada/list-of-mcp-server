"""OAuth client example for connecting to FastMCP servers.

This example demonstrates how to connect to an OAuth-protected FastMCP server.

Usage:
    python client.py login
    python client.py list-tools
    python client.py logout
"""

import asyncio
import sys
from fastmcp.client import Client

SERVER_URL = "http://127.0.0.1:8000/mcp"
client: Client | None = None


async def login():
    """Authenticate and connect to the FastMCP server."""
    global client
    try:
        client = Client(SERVER_URL, auth="oauth")
        await client.__aenter__()  # manually enter async context

        if not await client.ping():
            raise Exception("Ping failed after login.")

        print("✅ Successfully logged in!")
    except Exception as e:
        print(f"❌ Login failed: {e}")
        raise


async def logout():
    """Logout and close the client connection."""
    global client
    if client is not None:
        await client.__aexit__(None, None, None)
        print("👋 Logged out successfully.")
        client = None
    else:
        print("⚠️ No active session to logout.")


async def list_tools():
    """Fetch and display available tools."""
    global client
    if client is None:
        print("⚠️ Not logged in. Please login first.")
        return

    tools = await client.list_tools()
    print(f"🔧 Available tools ({len(tools)}):")
    for tool in tools:
        print(f"   - {tool.name}: {tool.description}")


async def main():
    if len(sys.argv) < 2:
        print("❌ Missing command. Use one of: login, list-tools, logout")
        return

    command = sys.argv[1]

    if command == "login":
        await login()
    elif command == "list-tools":
        await login()   # auto-login if not already
        await list_tools()
        await logout()
    elif command == "logout":
        await logout()
    else:
        print(f"❌ Unknown command: {command}")


if __name__ == "__main__":
    asyncio.run(main())

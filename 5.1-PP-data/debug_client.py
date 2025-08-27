import asyncio
import json
from contextlib import AsyncExitStack
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters

async def debug_connection():
    """Debug the MCP server connection and API calls."""
    exit_stack = AsyncExitStack()
    
    try:
        # Connect to the server
        server_params = StdioServerParameters(
            command="python",
            args=["server_2.py"],
        )
        
        stdio_transport = await exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        stdio, write = stdio_transport
        session = await exit_stack.enter_async_context(
            ClientSession(stdio, write)
        )
        
        await session.initialize()
        print("✅ Connected to MCP server")
        
        # Test connection
        print("\n🔍 Testing API connection...")
        result = await session.call_tool("test_connection", arguments={})
        print(f"Connection test result: {result.content[0].text}")
        
        # Debug headers
        print("\n🔍 Checking headers...")
        result = await session.call_tool("debug_headers", arguments={})
        print(f"Headers: {result.content[0].text}")
        
        # Debug base URL
        print("\n🔍 Checking base URL...")
        result = await session.call_tool("debug_base_url", arguments={})
        print(f"Base URL: {result.content[0].text}")
        
        # Try a simple API call
        print("\n🔍 Testing list_accounts...")
        result = await session.call_tool("list_accounts", arguments={})
        print(f"List accounts result: {result.content[0].text[:500]}...")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await exit_stack.aclose()

if __name__ == "__main__":
    asyncio.run(debug_connection())

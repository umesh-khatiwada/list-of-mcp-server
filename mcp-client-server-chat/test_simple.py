import asyncio
import json
from fastmcp.client import Client

def extract_result_data(result):
    """Extract the actual data from CallToolResult"""
    if hasattr(result, 'content') and result.content:
        if hasattr(result.content[0], 'text'):
            try:
                return json.loads(result.content[0].text)
            except json.JSONDecodeError:
                return result.content[0].text
    elif hasattr(result, 'data'):
        try:
            return json.loads(result.data)
        except json.JSONDecodeError:
            return result.data
    return str(result)

async def test_mcp_tools():
    """Test MCP tools using the FastMCP client"""
    
    # Connect to the MCP server
    async with Client(transport="http://127.0.0.1:8000/mcp") as client:
        print("Connected to MCP server")
        
        # List available tools
        print("\n=== Listing Tools ===")
        try:
            tools = await client.list_tools()
            # Handle different response formats
            if hasattr(tools, 'tools'):
                tool_list = tools.tools
            elif isinstance(tools, list):
                tool_list = tools
            else:
                tool_list = []
                
            print(f"Found {len(tool_list)} tools:")
            for tool in tool_list:
                if hasattr(tool, 'name'):
                    print(f"  • {tool.name}: {getattr(tool, 'description', 'No description')}")
                else:
                    print(f"  • {tool}")
        except Exception as e:
            print(f"Error listing tools: {e}")
        
        # Test health check
        print("\n=== Testing health_check ===")
        try:
            result = await client.call_tool("health_check", {})
            data = extract_result_data(result)
            print(f"Health check result: {json.dumps(data, indent=2)}")
        except Exception as e:
            print(f"Error calling health_check: {e}")
        
        # Test redis_get_token
        print("\n=== Testing redis_get_token ===")
        try:
            result = await client.call_tool("redis_get_token", {"key": "111"})
            data = extract_result_data(result)
            print(f"Redis get token result: {json.dumps(data, indent=2)}")
        except Exception as e:
            print(f"Error calling redis_get_token: {e}")
        
        # Test rss_feed_read
        print("\n=== Testing rss_feed_read ===")
        try:
            result = await client.call_tool("rss_feed_read", {})
            data = extract_result_data(result)
            print(f"RSS feed read result: {json.dumps(data, indent=2)}")
        except Exception as e:
            print(f"Error calling rss_feed_read: {e}")
            
        # Test perizer_data_curl_get (should fail without proper token)
        print("\n=== Testing perizer_data_curl_get ===")
        try:
            result = await client.call_tool("perizer_data_curl_get", {
                "url": "https://api.test.computesphere.com/api/v1/users",
                "parameters2_Value": "fake_token_123"
            })
            data = extract_result_data(result)
            print(f"API GET result: {json.dumps(data, indent=2)}")
        except Exception as e:
            print(f"Error calling perizer_data_curl_get: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp_tools())

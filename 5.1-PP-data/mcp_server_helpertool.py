import os
import json
from mcp.server.fastmcp import FastMCP
import redis.asyncio as redis
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Create an MCP server
mcp = FastMCP(
    name="Knowledge Base",
    host="0.0.0.0",  # only used for SSE transport (localhost)
    port=8050,  # only used for SSE transport (set this to any port)
)

@mcp.tool(name="redis_get_token", description="Get token from Redis")
async def redis_get_token(key: str) -> str:
    """Get token from Redis"""
    try:
        redis_url = os.getenv('REDIS_URL')
        print(f"Redis URL: {redis_url}")
        try:
            redis_client = redis.from_url(redis_url, decode_responses=True)
            token = await redis_client.get(key)
            await redis_client.close()
            
            if token:
                result = json.dumps({"success": True, "token": token, "key": key, "source": "redis"})
                print(f"Successfully retrieved token from Redis for key '{key}': {result}")
                return result
            else:
                print(f"Token not found in Redis for key '{key}', using mock data")
        except Exception as redis_error:
            print(f"Redis error: {redis_error}, falling back to mock data")
            
    except Exception as e:
        error_result = json.dumps({"error": str(e), "key": key})
        print(f"Exception in redis_get_token: {error_result}")
        return error_result


# Run the server
if __name__ == "__main__":
    print("🚀 Starting Helper Tool MCP Server...")
    print(f"Redis URL from env: {os.getenv('REDIS_URL', 'NOT_SET')}")
    mcp.run(transport="stdio")
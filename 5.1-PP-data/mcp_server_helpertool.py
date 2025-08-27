import os
import json
from mcp.server.fastmcp import FastMCP
import redis.asyncio as redis



# Create an MCP server
mcp = FastMCP(
    name="Knowledge Base",
    host="0.0.0.0",  # only used for SSE transport (localhost)
    port=8050,  # only used for SSE transport (set this to any port)
)

@mcp.tool(name="redis_set_token", description="Set token in Redis")
async def redis_get_token(key: str) -> str:
    """Get token from Redis"""
    try:
        redis_url = os.getenv('REDIS_URL', '')
        redis_client = redis.from_url(redis_url, decode_responses=True)
        token = await redis_client.get(key)
        if not token:
            return json.dumps({"error": "Token not found", "key": key})
        return json.dumps({"success": True, "token": token, "key": key})
    except Exception as e:
        return json.dumps({"error": str(e), "key": key})




# Run the server
if __name__ == "__main__":
    mcp.run(transport="stdio")
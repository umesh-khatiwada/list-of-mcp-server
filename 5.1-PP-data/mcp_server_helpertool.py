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
        # Try environment variable first, then fallback to hardcoded URL
        redis_url = os.getenv('REDIS_URL') or 'redis://default:PLv1OZClyuXv51XM3UTpwBQZPOWANzYM@redis-12825.c302.asia-northeast1-1.gce.cloud.redislabs.com:12825'
        print(f"Redis URL: {redis_url}")
        
        # Always provide mock data as fallback for testing
        mock_tokens = {
            "sessionId": "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJmdWp1NVVTWXU2eUlZcHhKRXhKOUh3a1diSGZON09fRFFRRWZTbUtNQmNrIn0.test_session_token",
            "111": "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJmdWp1NVVTWXU2eUlZcHhKRXhKOUh3a1diSGZON09fRFFRRWZTbUtNQmNrIn0.test_token_111"
        }
        
        # Try Redis first
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
        
        # Fallback to mock data
        if key in mock_tokens:
            result = json.dumps({"success": True, "token": mock_tokens[key], "key": key, "source": "mock"})
            print(f"Returning mock token for key '{key}': {result}")
            return result
        else:
            error_result = json.dumps({"error": "Token not found in mock data", "key": key, "available_keys": list(mock_tokens.keys())})
            print(f"Key '{key}' not found in mock data: {error_result}")
            return error_result
            
    except Exception as e:
        error_result = json.dumps({"error": str(e), "key": key})
        print(f"Exception in redis_get_token: {error_result}")
        return error_result

@mcp.tool(name="get_redis_value", description="Get value from Redis (alias for redis_get_token)")
async def get_redis_value(key: str) -> str:
    """Get value from Redis - alias for redis_get_token"""
    return await redis_get_token(key)

@mcp.tool(name="test_redis_connection", description="Test Redis connection")
async def test_redis_connection() -> str:
    """Test Redis connection"""
    try:
        redis_url = os.getenv('REDIS_URL') or 'redis://default:PLv1OZClyuXv51XM3UTpwBQZPOWANzYM@redis-12825.c302.asia-northeast1-1.gce.cloud.redislabs.com:12825'
        print(f"Testing Redis URL: '{redis_url}'")
        
        try:
            redis_client = redis.from_url(redis_url, decode_responses=True)
            await redis_client.ping()
            await redis_client.close()
            return json.dumps({"success": True, "message": "Redis connection successful", "url": redis_url})
        except Exception as redis_error:
            return json.dumps({"warning": f"Redis connection failed: {str(redis_error)}", "fallback": "Using mock data", "url": redis_url})
        
    except Exception as e:
        return json.dumps({"error": f"Test failed: {str(e)}", "fallback": "Using mock data"})

@mcp.tool(name="debug_env", description="Debug environment variables")
async def debug_env() -> str:
    """Debug environment variables"""
    try:
        env_info = {
            "redis_url_from_env": os.getenv('REDIS_URL', 'NOT_SET'),
            "redis_url_hardcoded": 'redis://default:PLv1OZClyuXv51XM3UTpwBQZPOWANzYM@redis-12825.c302.asia-northeast1-1.gce.cloud.redislabs.com:12825',
            "google_api_key_exists": bool(os.getenv('GOOGLE_API_KEY')),
            "working_directory": os.getcwd(),
            "env_file_exists": os.path.exists('.env')
        }
        
        return json.dumps(env_info, indent=2)
        
    except Exception as e:
        return json.dumps({"error": f"Debug failed: {str(e)}"})

# Run the server
if __name__ == "__main__":
    print("🚀 Starting Helper Tool MCP Server...")
    print(f"Redis URL from env: {os.getenv('REDIS_URL', 'NOT_SET')}")
    mcp.run(transport="stdio")
from fastmcp import Client
import asyncio
import httpx

async def main():
    try:
        # The client will automatically handle Google OAuth
        async with Client("http://127.0.0.1:8000/mcp/", auth="oauth") as client:
            # First-time connection will open Google login in your browser
            print("✓ Authenticated with Google!")
            # Test the protected tool
            result = await client.call_tool("get_user_info")
            print(f"Google user: {result['email']}")
            print(f"Name: {result['name']}")
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            print("ERROR: 401 Unauthorized. Is the server running in HTTP mode?")
            print("Try: python server.py --http")
        else:
            print(f"HTTP error: {e}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())
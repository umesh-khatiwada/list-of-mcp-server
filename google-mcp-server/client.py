from fastmcp import Client
import asyncio
import httpx

async def main():
    try:
        async with Client("http://localhost:8000/mcp", auth="oauth") as client:
            print("✓ Authenticated with Google!")

            # List available tools
            tools = await client.list_tools()
            print("Available tools:", [t['name'] for t in tools])

            # Call the protected tool
            result = await client.call_tool("get_user_info")
            print("Google user:", result.get("email"))
            print("Name:", result.get("name"))

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            print("❌ 401 Unauthorized – check that:")
            print("   • Server base_url uses localhost (not localhost)")
            print("   • Client URL matches exactly (http://localhost:8000/mcp)")
            print("   • Google OAuth credentials are correct")
        else:
            print(f"HTTP error: {e}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())

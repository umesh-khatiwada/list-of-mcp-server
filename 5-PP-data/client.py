import asyncio

from fastmcp import Client


async def main():
    # Connect to the MCP server we just created
    async with Client("http://127.0.0.1:8000/mcp/") as client:
        # List the tools that were automatically generated
        tools = await client.list_tools()
        print("Generated Tools:")
        for tool in tools:
            print(f"- {tool.name}")

        # Call one of the generated tools
        print("\n\nCalling tool 'update_project_alert_notifications'...")
        accounts = await client.call_tool("update_project_alert_notifications")
        print(f"Result:\n{accounts.data}")


if __name__ == "__main__":
    asyncio.run(main())

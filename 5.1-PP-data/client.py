import asyncio
import json
import os
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional

import nest_asyncio
from dotenv import load_dotenv
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
from openai import AsyncOpenAI

# Allow nested event loops (needed for Jupyter/IPython)
nest_asyncio.apply()
load_dotenv(".env")


class MCPServerClient:
    """Represents a single MCP server connection."""

    def __init__(self, name: str, server_script: str):
        self.name = name
        self.server_script = server_script
        self.session: Optional[ClientSession] = None
        self.stdio: Optional[Any] = None
        self.write: Optional[Any] = None
        self.tools: Dict[str, Dict[str, Any]] = {}

    async def connect(self, exit_stack: AsyncExitStack):
        server_params = StdioServerParameters(
            command="python",
            args=[self.server_script],
        )
        stdio_transport = await exit_stack.enter_async_context(
            stdio_client(server_params)
        )
        self.stdio, self.write = stdio_transport
        self.session = await exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )
        await self.session.initialize()

        # List tools
        tools_result = await self.session.list_tools()
        for tool in tools_result.tools:
            self.tools[tool.name] = {
                "description": tool.description,
                "parameters": tool.inputSchema,
            }

        print(f"\n✅ Connected to server '{self.name}' with tools:")
        for tool in self.tools:
            print(f"  - {tool}: {self.tools[tool]['description']}")


class MCPOpenAIClient:
    """OpenAI client supporting multiple MCP servers with fallback."""

    def __init__(self, model: str = "gemini-2.5-flash"):
        self.exit_stack = AsyncExitStack()
        self.openai_client = AsyncOpenAI(
            api_key=os.getenv("GOOGLE_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        self.model = model
        self.servers: Dict[str, MCPServerClient] = {}

    async def add_server(self, name: str, server_script: str):
        server_client = MCPServerClient(name, server_script)
        await server_client.connect(self.exit_stack)
        self.servers[name] = server_client

    def find_tool_server(self, tool_name: str) -> Optional[MCPServerClient]:
        for server in self.servers.values():
            if tool_name in server.tools:
                return server
        return None

    async def get_all_tools(self) -> List[Dict[str, Any]]:
        """Aggregate all server tools for OpenAI tool integration."""
        tools_list = []
        for server in self.servers.values():
            for name, meta in server.tools.items():
                tools_list.append({
                    "type": "function",
                    "function": {
                        "name": name,
                        "description": meta["description"],
                        "parameters": meta["parameters"],
                    },
                })
        return tools_list

    async def process_query(self, query: str) -> str:
        tools = await self.get_all_tools()

        # Initial OpenAI request with all tools
        response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": query}],
            tools=tools,
            tool_choice="auto",
        )
        assistant_message = response.choices[0].message
        messages = [{"role": "user", "content": query}, assistant_message]

        # If there are tool calls, process them
        if assistant_message.tool_calls:
            for tool_call in assistant_message.tool_calls:
                server = self.find_tool_server(tool_call.function.name)
                if not server:
                    return f"⚠️ Tool '{tool_call.function.name}' not found on any server."

                result = await server.session.call_tool(
                    tool_call.function.name,
                    arguments=json.loads(tool_call.function.arguments),
                )
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result.content[0].text,
                })

            # Final response after tool execution
            final_response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="none",
            )
            return final_response.choices[0].message.content

        # No tool calls; fallback to general OpenAI response
        return assistant_message.content

    async def cleanup(self):
        await self.exit_stack.aclose()


async def main():
    client = MCPOpenAIClient()

    try:
        # Add multiple MCP servers
        await client.add_server("server1", "server.py")
        await client.add_server("server2", "server_2.py")

        print("\n✅ Connected! Type your questions (or 'exit' to quit)\n")
        while True:
            query = input("You: ").strip()
            if query.lower() in {"exit", "quit"}:
                break
            try:
                response = await client.process_query(query)
                print(f"\nAssistant: {response}\n")
            except Exception as e:
                print(f"⚠️ Error: {e}")

    finally:
        await client.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, RuntimeError, asyncio.CancelledError):
        pass

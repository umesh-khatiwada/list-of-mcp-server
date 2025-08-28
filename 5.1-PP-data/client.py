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
        print(f"Session ID for server '{self.name}': {getattr(self.session, 'session_id', 'N/A')}")

        # List tools
        tools_result = await self.session.list_tools()
        for tool in tools_result.tools:
            self.tools[tool.name] = {
                "description": tool.description,
                "parameters": tool.inputSchema,
            }

        print(f"\n Connected to server '{self.name}' with tools:")
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
        self.system_prompt = (
            "You are a helpful AI assistant that MUST follow this exact workflow for EVERY user query.\n"
            "\n"
            "MANDATORY 2-STEP WORKFLOW (NO EXCEPTIONS):\n"
            "\n"
            "Step 1: ALWAYS call 'redis_get_token' first\n"
            "- Call redis_get_token with key='111'\n"
            "- Extract the token from the response JSON\n"
            "\n"
            "Step 2: ALWAYS call the API tool second\n"
            "- For notification settings: call 'get_notification_settings'\n"
            "- For projects: call 'get_user_projects'\n"
            "- For accounts: call 'list_accounts'\n"
            "\n"
            "CRITICAL REQUIREMENTS:\n"
            "- You MUST make EXACTLY 2 tool calls for every request\n"
            "- NEVER make just 1 tool call - always make 2\n"
            "- First call: redis_get_token\n"
            "- Second call: the appropriate API tool\n"
            "- If you don't make 2 calls, you are failing\n"
            "\n"
            "EXAMPLE for 'get notification settings':\n"
            "1. Call redis_get_token(key='111')\n"
            "2. Call get_notification_settings()\n"
            "3. Format response nicely\n"
            "\n"
            "Available API tools: get_notification_settings, get_user_projects, list_accounts, etc.\n"
            "Remember: ALWAYS 2 calls, never 1!\n"
        )

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

        # Create messages with system prompt
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": query}
        ]

        print(f"🔍 Processing query with {len(tools)} available tools")

        # Initial OpenAI request with all tools - force tool calls
        response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto",  # Force tool usage
        )
        assistant_message = response.choices[0].message
        messages.append(assistant_message)

        tool_calls_made = len(assistant_message.tool_calls or [])
        print(f"🔍 AI wants to call {tool_calls_made} tools")

        # If AI didn't make enough tool calls, force it to continue
        if tool_calls_made == 1:
            print("⚠️ AI only made 1 tool call, forcing it to make the second call...")
            
            # Process the first tool call
            if assistant_message.tool_calls:
                tool_call = assistant_message.tool_calls[0]
                server = self.find_tool_server(tool_call.function.name)
                if server:
                    print(f"🔧 [1] Calling tool: {tool_call.function.name} with args: {tool_call.function.arguments}")
                    
                    result = await server.session.call_tool(
                        tool_call.function.name,
                        arguments=json.loads(tool_call.function.arguments),
                    )
                    result_content = result.content[0].text
                    print(f"✅ [1] Tool result: {result_content[:100]}...")
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result_content,
                    })
            
            # Force the AI to make the second tool call
            follow_up_prompt = "Now you MUST call the appropriate API tool to fulfill the user's request. You have the token, now get the data they asked for."
            messages.append({"role": "user", "content": follow_up_prompt})
            
            # Second OpenAI request to force the API call
            second_response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=tools,
                tool_choice="auto",
            )
            
            second_assistant_message = second_response.choices[0].message
            messages.append(second_assistant_message)
            
            # Process the second tool call
            if second_assistant_message.tool_calls:
                for i, tool_call in enumerate(second_assistant_message.tool_calls):
                    server = self.find_tool_server(tool_call.function.name)
                    if server:
                        print(f"🔧 [2] Calling tool: {tool_call.function.name} with args: {tool_call.function.arguments}")
                        
                        result = await server.session.call_tool(
                            tool_call.function.name,
                            arguments=json.loads(tool_call.function.arguments),
                        )
                        result_content = result.content[0].text
                        print(f"✅ [2] Tool result: {result_content[:100]}...")
                        
                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result_content,
                        })
        
        elif tool_calls_made >= 2:
            # AI made 2+ tool calls, process them normally
            for i, tool_call in enumerate(assistant_message.tool_calls):
                server = self.find_tool_server(tool_call.function.name)
                if not server:
                    return f"⚠️ Tool '{tool_call.function.name}' not found on any server."

                print(f"🔧 [{i+1}] Calling tool: {tool_call.function.name} with args: {tool_call.function.arguments}")
                
                try:
                    result = await server.session.call_tool(
                        tool_call.function.name,
                        arguments=json.loads(tool_call.function.arguments),
                    )
                    result_content = result.content[0].text
                    print(f"✅ [{i+1}] Tool result: {result_content[:100]}...")
                    
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result_content,
                    })
                except Exception as e:
                    error_msg = f"Error calling {tool_call.function.name}: {str(e)}"
                    print(f"❌ [{i+1}] {error_msg}")
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": error_msg,
                    })
        
        else:
            # AI made no tool calls - this shouldn't happen
            print("⚠️ AI made no tool calls - forcing manual workflow")
            return "I need to use tools to help you. Let me try again with the correct workflow."

        # Final response after all tool execution
        print("🔍 Getting final response from AI...")
        final_response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="none",
        )
        final_content = final_response.choices[0].message.content
        
        if final_content:
            print(f"✅ Final AI response: {final_content[:100]}...")
            return final_content
        else:
            print("⚠️ AI returned empty response")
            return "I retrieved the data but couldn't format a proper response. The tools worked correctly - please try asking again."

    async def cleanup(self):
        await self.exit_stack.aclose()


async def main():
    client = MCPOpenAIClient()
    try:
        # Add multiple MCP servers
        await client.add_server("helper_tool", "mcp_server_helpertool.py")
        await client.add_server("openapi", "mcp_server_openapi.py")

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

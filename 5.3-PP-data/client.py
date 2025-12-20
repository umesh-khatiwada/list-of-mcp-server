import asyncio
import json
import os
import uuid
from collections import deque
from contextlib import AsyncExitStack
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import nest_asyncio
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI

# Allow nested event loops (needed for Jupyter/IPython)
nest_asyncio.apply()
session_id = str(uuid.uuid4())
load_dotenv(".env")


class ConversationMemory:
    """Manages conversation context window with a maximum of 5 exchanges."""

    def __init__(self, max_windows: int = 5):
        self.max_windows = max_windows
        self.conversation_history: deque = deque(maxlen=max_windows * 2)
        self.system_prompt = None
        self.last_api_response = None  # Cache last API response
        self.last_api_call = None  # Cache last API call info
        self.session_id = session_id  # Unique session ID
        self.session_start_time = datetime.now().isoformat()
        self.message_count = 0

    def add_user_message(self, message: str):
        """Add a user message to the conversation history."""
        self.message_count += 1
        message_data = {
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat(),
            "message_id": str(uuid.uuid4()),
            "session_id": session_id,
        }
        self.conversation_history.append(message_data)

    def add_assistant_message(self, message: str):
        """Add an assistant message to the conversation history."""
        self.message_count += 1
        message_data = {
            "role": "assistant",
            "content": message,
            "timestamp": datetime.now().isoformat(),
            "message_id": str(uuid.uuid4()),
            "session_id": session_id,
        }
        self.conversation_history.append(message_data)

    def get_conversation_context(self) -> List[Dict]:
        """Get the current conversation context including system prompt."""
        messages = []

        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})

        # Add conversation history - only user and assistant messages, no tool calls
        for msg in self.conversation_history:
            if msg.get("role") in ["user", "assistant"]:
                # Clean message for AI (remove metadata)
                clean_msg = {"role": msg["role"], "content": msg["content"]}
                messages.append(clean_msg)

        return messages

    def set_system_prompt(self, prompt: str):
        """Set the system prompt."""
        self.system_prompt = prompt

    def clear_history(self):
        """Clear conversation history but keep system prompt."""
        self.conversation_history.clear()

    def get_context_summary(self) -> str:
        """Get a summary of the current context window."""
        len(self.conversation_history)
        user_messages = sum(
            1 for msg in self.conversation_history if msg.get("role") == "user"
        )
        assistant_messages = sum(
            1 for msg in self.conversation_history if msg.get("role") == "assistant"
        )

        return f"Session: {self.session_id[:8]}... | Context: {user_messages} user, {assistant_messages} assistant messages (max {self.max_windows} windows)"

    def get_session_info(self) -> Dict:
        """Get detailed session information."""
        return {
            "session_id": self.session_id,
            "start_time": self.session_start_time,
            "message_count": self.message_count,
            "total_messages": len(self.conversation_history),
            "has_cached_response": bool(self.last_api_response),
            "last_api_call": self.last_api_call.get("tool_name")
            if self.last_api_call
            else None,
        }

    def cache_api_response(
        self, api_call: str, response_data: str, parameters: dict = None
    ):
        """Cache the last API response for formatting requests."""
        self.last_api_response = response_data
        self.last_api_call = {
            "tool_name": api_call,
            "parameters": parameters or {},
            "timestamp": asyncio.get_event_loop().time(),
            "session_id": self.session_id,
            "call_id": str(uuid.uuid4()),
        }

    def get_cached_response(self) -> Optional[str]:
        """Get cached API response if available and recent."""
        if self.last_api_response and self.last_api_call:
            # Cache is valid for 5 minutes
            current_time = asyncio.get_event_loop().time()
            if current_time - self.last_api_call["timestamp"] < 300:
                return self.last_api_response
        return None

    def get_last_api_call_info(self) -> Optional[dict]:
        """Get information about the last API call."""
        return self.last_api_call


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
        print(
            f"Session ID for server '{self.name}': {getattr(self.session, 'session_id', 'N/A')}"
        )

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


class BaseAgent:
    """Base agent class with tool registration and query capabilities."""

    def __init__(self, model: str, api_key: str, base_url: str):
        self.model = model
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.tools: Dict[str, Dict[str, Any]] = {}
        self.tool_functions: Dict[str, Callable] = {}

    def register_tool(
        self, name: str, description: str, parameters: dict, function: Callable
    ):
        """Register a tool with the agent."""
        self.tools[name] = {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters,
            },
        }
        self.tool_functions[name] = function
        print(f"🔧 Registered tool: {name}")

    async def query(self, message: str, use_tools: bool = True) -> str:
        """Query the agent with optional tool usage."""
        messages = [{"role": "user", "content": message}]

        if use_tools and self.tools:
            # Initial request with tools
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=list(self.tools.values()),
                tool_choice="auto",
            )

            assistant_message = response.choices[0].message

            # Process tool calls if any
            if assistant_message.tool_calls:
                messages.append(assistant_message)

                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    arguments = json.loads(tool_call.function.arguments)

                    # Execute the tool function
                    if tool_name in self.tool_functions:
                        try:
                            result = await self.tool_functions[tool_name](**arguments)
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": str(result),
                                }
                            )
                        except Exception as e:
                            messages.append(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": f"Error: {str(e)}",
                                }
                            )

                # Get final response after tool execution
                final_response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tool_choice="none",
                )
                return final_response.choices[0].message.content
            else:
                return assistant_message.content
        else:
            # Simple query without tools
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tool_choice="none",
            )
            return response.choices[0].message.content


class MCPStrandsAgent(BaseAgent):
    """Custom agent supporting multiple MCP servers with memory management."""

    def __init__(self, model: str = "gemini-2.5-flash", memory_windows: int = 5):
        # Initialize Base Agent
        super().__init__(
            model=model,
            api_key=os.getenv("GOOGLE_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )

        self.exit_stack = AsyncExitStack()
        self.servers: Dict[str, MCPServerClient] = {}
        self.memory = ConversationMemory(max_windows=memory_windows)
        self.client_session_id = session_id  # Overall client session ID

        # Tools that require sessionId (authenticated tools with @with_token_middleware)
        self.authenticated_tools = {
            "get_home",
            "get_user_projects",
            "get_notifications",
            "get_notification_count",
            "get_notification_settings",
        }

        system_prompt = (
            "You are a helpful AI assistant that can access the Computesphere API via a custom agent framework.\n"
            "\n"
            "FOR AUTHENTICATED OPERATIONS:\n"
            "- Some tools automatically handle authentication via session tokens\n"
            "- These tools include: get_home, get_user_projects, get_notifications, get_notification_count, get_notification_settings\n"
            "- You can call these tools directly - no need to get tokens manually\n"
            "- The system will automatically handle session-based authentication\n"
            "\n"
            "FOR NON-AUTHENTICATED OPERATIONS:\n"
            "- Some tools work without authentication (like list_plans, get_plan, etc.)\n"
            "- Call these tools directly as needed\n"
            "\n"
            "FOR FORMATTING REQUESTS (same data, different format):\n"
            "- Do NOT make any tool calls\n"
            "- Use the cached data provided in the context\n"
            "- Apply the requested formatting to the existing data\n"
            "\n"
            "FORMATTING KEYWORDS: 'in list format', 'as table', 'title only', etc.\n"
            "\n"
            "Remember: The system handles authentication automatically for user-specific data!\n"
        )

        self.memory.set_system_prompt(system_prompt)

    async def add_server(self, name: str, server_script: str):
        """Add an MCP server and register its tools with the agent."""
        server_client = MCPServerClient(name, server_script)
        await server_client.connect(self.exit_stack)
        self.servers[name] = server_client

        # Register MCP tools with Strands
        await self._register_mcp_tools(server_client)

    async def _register_mcp_tools(self, server_client: MCPServerClient):
        """Register MCP server tools with the custom agent."""
        for tool_name, tool_meta in server_client.tools.items():
            # Create a wrapper function for each MCP tool
            async def mcp_tool_wrapper(tool_name=tool_name, **kwargs):
                # Inject sessionId for authenticated tools
                if tool_name in self.authenticated_tools:
                    kwargs["sessionId"] = session_id
                    print(f"Injected sessionId for authenticated tool: {tool_name}")

                # Find the server for this tool
                server = self.find_tool_server(tool_name)
                if not server:
                    return f"Tool '{tool_name}' not found on any server."

                try:
                    result = await server.session.call_tool(tool_name, arguments=kwargs)
                    result_content = result.content[0].text
                    print(
                        f"🔧 Called tool: {tool_name} with result: {result_content[:100]}..."
                    )

                    # Cache API responses for formatting requests
                    if tool_name != "redis_get_token":
                        self.memory.cache_api_response(
                            tool_name, result_content, kwargs
                        )

                    return result_content
                except Exception as e:
                    error_msg = f"Error calling {tool_name}: {str(e)}"
                    print(f"❌ {error_msg}")
                    return error_msg

            # Register the tool with the custom agent
            self.register_tool(
                name=tool_name,
                description=tool_meta["description"],
                parameters=tool_meta["parameters"],
                function=mcp_tool_wrapper,
            )

    def find_tool_server(self, tool_name: str) -> Optional[MCPServerClient]:
        """Find which server has a specific tool."""
        for server in self.servers.values():
            if tool_name in server.tools:
                return server
        return None

    async def process_query(self, query: str) -> str:
        """Process user query using custom agent with MCP tools."""
        # Add user message to memory
        self.memory.add_user_message(query)

        # Check if this is a formatting request
        is_formatting_request = self._is_formatting_request(query)
        cached_response = (
            self.memory.get_cached_response() if is_formatting_request else None
        )

        print(f"🔍 Processing query with custom agent")
        print(f"📊 {self.memory.get_context_summary()}")
        session_info = self.memory.get_session_info()
        print(
            f"🆔 Query ID: {str(uuid.uuid4())[:8]}... | Session: {session_info['session_id'][:8]}..."
        )

        if is_formatting_request and cached_response:
            print("🔄 Detected formatting request - using cached data (no API calls)")
            # Use agent to format cached data without tool calls
            format_query = f"Format this data according to the request '{query}':\n\n{cached_response}"
            formatted_response = await self.query(format_query, use_tools=False)

            if formatted_response:
                print(f"✅ Formatted response using cached data")
                self.memory.add_assistant_message(formatted_response)
                return formatted_response
            else:
                print(
                    "⚠️ Failed to format cached data, falling back to normal processing"
                )

        # Use custom agent to process the query with tools
        try:
            response = await self.query(query, use_tools=True)

            if response:
                print(f"✅ Custom agent response: {response[:100]}...")
                self.memory.add_assistant_message(response)
                return response
            else:
                error_msg = "The agent couldn't process your request. Please try again."
                self.memory.add_assistant_message(error_msg)
                return error_msg

        except Exception as e:
            error_msg = f"Error processing query: {str(e)}"
            print(f"❌ {error_msg}")
            self.memory.add_assistant_message(error_msg)
            return error_msg

    def clear_memory(self):
        """Clear conversation memory and start new session."""
        old_session = self.memory.session_id[:8]
        self.memory.clear_history()
        # Create new session
        self.memory.session_id = str(uuid.uuid4())
        self.memory.session_start_time = datetime.now().isoformat()
        self.memory.message_count = 0
        print(
            f"🧹 Conversation memory cleared. New session: {self.memory.session_id[:8]}... (Previous: {old_session}...)"
        )

    def get_memory_status(self) -> str:
        """Get current memory status."""
        return self.memory.get_context_summary()

    def get_session_details(self) -> Dict:
        """Get detailed session information."""
        session_info = self.memory.get_session_info()
        session_info["client_session_id"] = self.client_session_id
        return session_info

    def _is_formatting_request(self, query: str) -> bool:
        """Check if the query is asking for a format change of previous data."""
        formatting_keywords = [
            "in list format",
            "as list",
            "list format",
            "in table",
            "as table",
            "title only",
            "titles only",
            "just titles",
            "only titles",
            "differently",
            "different format",
            "format it",
            "show as",
            "display as",
            "present as",
            "same data",
            "same thing",
            "format in",
            "format as",
            "reformat",
        ]
        query_lower = query.lower().strip()
        return any(keyword in query_lower for keyword in formatting_keywords)

    def _get_previous_api_call(self) -> Optional[str]:
        """Extract the last API call from conversation history."""
        # Look through recent messages for API-related calls
        for msg in reversed(list(self.memory.conversation_history)):
            if msg.get("role") == "user":
                content = msg.get("content", "").lower()
                if "notification" in content:
                    return "get_notifications"
                elif "project" in content:
                    return "get_user_projects"
                elif "account" in content:
                    return "list_accounts"
        return "get_notifications"  # Default fallback

    async def cleanup(self):
        """Clean up resources."""
        await self.exit_stack.aclose()


async def main():
    client = MCPStrandsAgent(memory_windows=5)

    print(f"🚀 Starting MCP Client - Session: {client.client_session_id}...")

    try:
        # Add MCP server via stdio transport
        await client.add_server("openapi", "mcp_server_openapi.py")

        print("\n Connected! Type your questions (or 'exit' to quit)")
        print(" Commands: 'clear memory', 'memory status', 'session info'")
        print(f" {client.get_memory_status()}\n")

        while True:
            query = input("You: ").strip()
            if query.lower() in {"exit", "quit"}:
                break
            elif query.lower() == "clear memory":
                client.clear_memory()
                continue
            elif query.lower() == "memory status":
                print(f" {client.get_memory_status()}")
                continue
            elif query.lower() == "session info":
                session_details = client.get_session_details()
                print(f"Session Details:")
                print(f"   Client Session ID: {session_details['client_session_id']}")
                print(f"   Conversation Session ID: {session_details['session_id']}")
                print(f"   Start Time: {session_details['start_time']}")
                print(f"   Message Count: {session_details['message_count']}")
                print(
                    f"   Total Messages in Memory: {session_details['total_messages']}"
                )
                print(
                    f"   Has Cached Response: {session_details['has_cached_response']}"
                )
                print(f"   Last API Call: {session_details['last_api_call'] or 'None'}")
                continue

            try:
                response = await client.process_query(query)
                print(f"\nAssistant: {response}\n")
                print(f" {client.get_memory_status()}")
            except Exception as e:
                print(f" Error: {e}")
    finally:
        await client.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, RuntimeError, asyncio.CancelledError):
        pass

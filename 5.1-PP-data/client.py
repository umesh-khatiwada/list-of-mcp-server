import asyncio
import json
import os
import uuid
from contextlib import AsyncExitStack
from typing import Any, Dict, List, Optional
from collections import deque
from datetime import datetime

import nest_asyncio
from dotenv import load_dotenv
from mcp.client.stdio import stdio_client
from mcp import ClientSession, StdioServerParameters
from openai import AsyncOpenAI

# Allow nested event loops (needed for Jupyter/IPython)
nest_asyncio.apply()
load_dotenv(".env")

class ConversationMemory:
    """Manages conversation context window with a maximum of 5 exchanges."""
    
    def __init__(self, max_windows: int = 5):
        self.max_windows = max_windows
        self.conversation_history: deque = deque(maxlen=max_windows * 2)
        self.system_prompt = None
        self.last_api_response = None  # Cache last API response
        self.last_api_call = None      # Cache last API call info
        self.session_id = str(uuid.uuid4())  # Unique session ID
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
            "session_id": self.session_id
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
            "session_id": self.session_id
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
        total_messages = len(self.conversation_history)
        user_messages = sum(1 for msg in self.conversation_history if msg.get("role") == "user")
        assistant_messages = sum(1 for msg in self.conversation_history if msg.get("role") == "assistant")
        
        return f"Session: {self.session_id[:8]}... | Context: {user_messages} user, {assistant_messages} assistant messages (max {self.max_windows} windows)"
    
    def get_session_info(self) -> Dict:
        """Get detailed session information."""
        return {
            "session_id": self.session_id,
            "start_time": self.session_start_time,
            "message_count": self.message_count,
            "total_messages": len(self.conversation_history),
            "has_cached_response": bool(self.last_api_response),
            "last_api_call": self.last_api_call.get("tool_name") if self.last_api_call else None
        }
    
    def cache_api_response(self, api_call: str, response_data: str, parameters: dict = None):
        """Cache the last API response for formatting requests."""
        self.last_api_response = response_data
        self.last_api_call = {
            "tool_name": api_call,
            "parameters": parameters or {},
            "timestamp": asyncio.get_event_loop().time(),
            "session_id": self.session_id,
            "call_id": str(uuid.uuid4())
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
    def __init__(self, model: str = "gemini-2.5-flash", memory_windows: int = 5):
        self.exit_stack = AsyncExitStack()
        self.openai_client = AsyncOpenAI(
            api_key=os.getenv("GOOGLE_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        self.model = model
        self.servers: Dict[str, MCPServerClient] = {}
        self.memory = ConversationMemory(max_windows=memory_windows)
        self.client_session_id = str(uuid.uuid4())  # Overall client session ID
        
        system_prompt = (
            "You are a helpful AI assistant that MUST follow specific workflows.\n"
            "\n"
            " CRITICAL RULE: ALWAYS GET AUTHORIZATION TOKEN FIRST! \n"
            "\n"
            "FOR NEW DATA REQUESTS - MANDATORY 2-STEP WORKFLOW:\n"
            "Step 1: FIRST - Call redis_get_token with key='111' (to get authorization)\n"
            "Step 2: SECOND - Call the appropriate API tool\n"
            "\n"
            "❌ NEVER call API tools without getting the token first!\n"
            "❌ NEVER call get_notification_settings before redis_get_token!\n"
            "❌ NEVER call get_user_projects before redis_get_token!\n"
            "❌ API calls will FAIL without proper authorization!\n"
            "\n"
            "✅ CORRECT ORDER EXAMPLES:\n"
            "1. User: 'get notification settings'\n"
            "   Step 1: redis_get_token(key='111') → get auth token\n"
            "   Step 2: get_notification_settings() → get the data\n"
            "\n"
            "2. User: 'show my projects'\n"
            "   Step 1: redis_get_token(key='111') → get auth token\n"
            "   Step 2: get_user_projects() → get the data\n"
            "\n"
            "FOR FORMATTING REQUESTS (same data, different format):\n"
            "- Do NOT make any tool calls\n"
            "- Use the cached data provided in the context\n"
            "- Apply the requested formatting to the existing data\n"
            "\n"
            "FORMATTING KEYWORDS: 'in list format', 'as table', 'title only', etc.\n"
            "\n"
            "Remember: AUTHORIZATION FIRST, API SECOND, ALWAYS!\n"
        )
        
        self.memory.set_system_prompt(system_prompt)

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
        
        # Add user message to memory with session tracking
        self.memory.add_user_message(query)
        
        # Check if this is a formatting request
        is_formatting_request = self._is_formatting_request(query)
        cached_response = self.memory.get_cached_response() if is_formatting_request else None
        
        print(f"🔍 Processing query with {len(tools)} available tools")
        print(f" {self.memory.get_context_summary()}")
        
        # Log session information
        session_info = self.memory.get_session_info()
        print(f"Query ID: {str(uuid.uuid4())[:8]}... | Session: {session_info['session_id'][:8]}...")
        
        if is_formatting_request and cached_response:
            print("🔄 Detected formatting request - using cached data (no API calls)")
            
            # Create context for formatting without making tool calls
            format_messages = [
                {"role": "system", "content": self.memory.system_prompt},
                {"role": "user", "content": f"Format this data according to the request '{query}':\n\n{cached_response}"}
            ]
            
            # Get formatted response without making tool calls
            format_response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=format_messages,
                tool_choice="none",  # Force no tool calls
            )
            
            formatted_content = format_response.choices[0].message.content
            if formatted_content:
                print(f" Formatted response using cached data")
                self.memory.add_assistant_message(formatted_content)
                return formatted_content
            else:
                print(" Failed to format cached data, falling back to API call")
        
        # Regular workflow for new data requests
        print("🔍 Making API calls for new data request")
        
        # Get conversation context
        messages = self.memory.get_conversation_context()
        
        # Initial OpenAI request
        response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice="auto",
        )
        assistant_message = response.choices[0].message

        tool_calls_made = len(assistant_message.tool_calls or [])
        print(f"🔍 AI wants to call {tool_calls_made} tools")

        # Create fresh context for tool execution
        tool_execution_messages = [
            {"role": "system", "content": self.memory.system_prompt},
            {"role": "user", "content": query}
        ]
        
        api_response_data = None
        api_call_info = None

        # Process tool calls (existing logic)
        if tool_calls_made == 1:
            # Process first tool call
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
                    print(f" [1] Tool result: {result_content[:100]}...")
                    
                    tool_execution_messages.append(assistant_message)
                    tool_execution_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result_content,
                    })
            
            # Force second tool call
            follow_up_prompt = "Now you MUST call the appropriate API tool to fulfill the user's request. You have the token, now get the data they asked for."
            tool_execution_messages.append({"role": "user", "content": follow_up_prompt})
            
            second_response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=tool_execution_messages,
                tools=tools,
                tool_choice="auto",
            )
            
            second_assistant_message = second_response.choices[0].message
            
            # Process second tool call and cache response
            if second_assistant_message.tool_calls:
                for tool_call in second_assistant_message.tool_calls:
                    server = self.find_tool_server(tool_call.function.name)
                    if server:
                        print(f"🔧 [2] Calling tool: {tool_call.function.name} with args: {tool_call.function.arguments}")
                        
                        result = await server.session.call_tool(
                            tool_call.function.name,
                            arguments=json.loads(tool_call.function.arguments),
                        )
                        result_content = result.content[0].text
                        print(f" [2] Tool result: {result_content[:100]}...")
                        
                        # Cache the API response
                        api_response_data = result_content
                        api_call_info = {
                            "tool_name": tool_call.function.name,
                            "parameters": json.loads(tool_call.function.arguments)
                        }
                        
                        tool_execution_messages.append(second_assistant_message)
                        tool_execution_messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result_content,
                        })

        elif tool_calls_made >= 2:
            # Process multiple tool calls
            tool_execution_messages.append(assistant_message)
            
            for i, tool_call in enumerate(assistant_message.tool_calls):
                server = self.find_tool_server(tool_call.function.name)
                if not server:
                    error_msg = f" Tool '{tool_call.function.name}' not found on any server."
                    self.memory.add_assistant_message(error_msg)
                    return error_msg

                print(f"🔧 [{i+1}] Calling tool: {tool_call.function.name} with args: {tool_call.function.arguments}")
                
                try:
                    result = await server.session.call_tool(
                        tool_call.function.name,
                        arguments=json.loads(tool_call.function.arguments),
                    )
                    result_content = result.content[0].text
                    print(f" [{i+1}] Tool result: {result_content[:100]}...")
                    
                    # Cache the last API call (not Redis)
                    if tool_call.function.name != "redis_get_token":
                        api_response_data = result_content
                        api_call_info = {
                            "tool_name": tool_call.function.name,
                            "parameters": json.loads(tool_call.function.arguments)
                        }
                    
                    tool_execution_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result_content,
                    })
                    
                except Exception as e:
                    error_msg = f"Error calling {tool_call.function.name}: {str(e)}"
                    print(f" [{i+1}] {error_msg}")
                    tool_execution_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": error_msg,
                    })
        
        else:
            # AI made no tool calls - this shouldn't happen
            print(" AI made no tool calls - forcing manual workflow")
            error_msg = "I need to use tools to help you. Let me try again with the correct workflow."
            self.memory.add_assistant_message(error_msg)
            return error_msg

        # Get final response
        print("🔍 Getting final response from AI...")
        final_response = await self.openai_client.chat.completions.create(
            model=self.model,
            messages=tool_execution_messages,
            tools=tools,
            tool_choice="none",
        )
        final_content = final_response.choices[0].message.content
        
        # Cache the API response for future formatting requests
        if api_response_data and api_call_info:
            self.memory.cache_api_response(
                api_call_info["tool_name"],
                api_response_data,
                api_call_info["parameters"]
            )
            print(f"💾 Cached API response for future formatting requests (Call ID: {self.memory.last_api_call['call_id'][:8]}...)")
        
        if final_content:
            print(f" Final AI response: {final_content[:100]}...")
            self.memory.add_assistant_message(final_content)
            return final_content
        else:
            print(" AI returned empty response")
            error_msg = "I retrieved the data but couldn't format a proper response. The tools worked correctly - please try asking again."
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
        print(f"🧹 Conversation memory cleared. New session: {self.memory.session_id[:8]}... (Previous: {old_session}...)")

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
            'in list format', 'as list', 'list format', 'in table', 'as table',
            'title only', 'titles only', 'just titles', 'only titles',
            'differently', 'different format', 'format it', 'show as',
            'display as', 'present as', 'same data', 'same thing',
            'format in', 'format as', 'reformat'
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


async def main():
    client = MCPOpenAIClient(memory_windows=5)
    
    print(f"🚀 Starting MCP Client - Session: {client.client_session_id}...")
    
    try:
        # Add multiple MCP servers
        await client.add_server("helper_tool", "mcp_server_helpertool.py")
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
                print(f"   Total Messages in Memory: {session_details['total_messages']}")
                print(f"   Has Cached Response: {session_details['has_cached_response']}")
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

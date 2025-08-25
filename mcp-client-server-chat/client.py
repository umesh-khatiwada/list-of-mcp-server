# ====================================
# ai_agent_client.py - Full AI Agent with HTTP MCP client
# ====================================

import asyncio
import json
import os
from typing import Any
import google.generativeai as genai
from fastmcp.client import Client
import time
import httpx


class MCPClient:
    """Client to communicate with MCP server tools via HTTP."""

    def __init__(self, server_url: str = "http://127.0.0.1:8000/mcp"):
        self.client: Client | None = None
        self.server_url = server_url

    async def __aenter__(self):
        # Use HTTP transport to connect to the server
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                print(f"Attempting to connect to server at {self.server_url} (attempt {attempt + 1}/{max_retries})")
                self.client = Client(transport=self.server_url)
                await self.client.__aenter__()
                print("Successfully connected to MCP server")
                return self
            except Exception as e:
                print(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    print(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    print("Failed to connect to server. Make sure the server is running on http://127.0.0.1:8000/mcp")
                    print("Start the server with: fastmcp run server.py --transport http --port 8000")
                    raise RuntimeError(f"Could not connect to MCP server after {max_retries} attempts")

    async def __aexit__(self, exc_type, exc, tb):
        if self.client:
            await self.client.__aexit__(exc_type, exc, tb)

    async def call_tool(self, tool_name: str, **kwargs) -> str:
        if not self.client:
            raise RuntimeError("MCP client not started. Use `async with MCPClient()`.")
        try:
            result = await self.client.call_tool(tool_name, kwargs)
            # Extract content from CallToolResult object
            if hasattr(result, 'content'):
                if isinstance(result.content, list) and len(result.content) > 0:
                    # Get the first content item
                    content_item = result.content[0]
                    if hasattr(content_item, 'text'):
                        return content_item.text
                    elif hasattr(content_item, 'data'):
                        return content_item.data
                return str(result.content)
            elif hasattr(result, 'result'):
                return json.dumps(result.result)
            else:
                return str(result)
        except Exception as e:
            return json.dumps({"error": f"MCP tool call failed: {str(e)}"})

    async def list_tools(self) -> str:
        """List available MCP tools"""
        if not self.client:
            raise RuntimeError("MCP client not started. Use `async with MCPClient()`.")
        try:
            tools = await self.client.list_tools()
            tool_list = []
            for tool in tools.tools:
                tool_info = {
                    "name": tool.name,
                    "description": tool.description or "No description available",
                    "input_schema": tool.inputSchema.model_dump() if hasattr(tool, 'inputSchema') else "No schema"
                }
                tool_list.append(tool_info)
            return json.dumps({"tools": tool_list}, indent=2)
        except Exception as e:
            return json.dumps({"error": f"Failed to list tools: {str(e)}"})

    async def list_tools_curl(self) -> str:
        """List available MCP tools using direct HTTP/curl request"""
        try:
            async with httpx.AsyncClient() as client:
                # First, try to initialize the session
                init_payload = {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {
                            "name": "test-client",
                            "version": "1.0.0"
                        }
                    }
                }
                
                # Initialize session
                init_response = await client.post(
                    "http://127.0.0.1:8000/mcp",
                    json=init_payload,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json,text/event-stream"
                    }
                )
                
                if init_response.status_code != 200:
                    return json.dumps({"error": f"Failed to initialize: HTTP {init_response.status_code}: {init_response.text}"})
                
                # Now list tools
                tools_payload = {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/list",
                    "params": {}
                }
                
                response = await client.post(
                    "http://127.0.0.1:8000/mcp",
                    json=tools_payload,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json,text/event-stream"
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    if "result" in result and "tools" in result["result"]:
                        tools = result["result"]["tools"]
                        formatted_tools = []
                        for tool in tools:
                            formatted_tools.append({
                                "name": tool.get("name", "Unknown"),
                                "description": tool.get("description", "No description"),
                                "input_schema": tool.get("inputSchema", {})
                            })
                        return json.dumps({"tools": formatted_tools}, indent=2)
                    else:
                        return json.dumps({"error": "No tools found in response", "response": result})
                else:
                    return json.dumps({"error": f"HTTP {response.status_code}: {response.text}"})

        except Exception as e:
            return json.dumps({"error": f"Failed to list tools via curl: {str(e)}"})


class AIAgent:
    """AI Agent that processes chat messages using MCP tools."""

    def __init__(self, mcp_client: MCPClient, ai_model):
        self.mcp_client = mcp_client
        self.ai_model = ai_model
        self.memory = {}

        # Full system prompt with instructions
        self.system_prompt = """
---
You are a helpful AI assistant designed to answer user questions based on requests.
Your responsibilities are:
---
###  Step 1: Retrieve Authorization Token
* Always begin by connecting to the **MCP client**.
* Fetch the "x-user-token" token from **Redis**, using:
  ```text
  key = {{ $json.sessionId }}
  ```
* The Redis output will contain the  token (e.g., `abc123...`).
* Extract this token and use it in all subsequent HTTP requests as:
  ```http
  x-user-token: <token>
  ```
 Important:
    The  x-user-token received from Redis must be used exactly as returned when sent in the header for API requests . 

    Extract the full  token string (e.g., abc123...).
    Store in window buffer memory as:
    {{ $json.sessionId }} =  abc123...
---
###  Step 2: Match Message with RSS Read
* Always check if the **chat message matches any path in RSS Read**.
* If found, identify the corresponding HTTP method: `GET`, `POST`, or `PUT`.
---
###  Step 3: Make the API Request
Use the appropriate tool and follow these rules based on the HTTP method:
#### If `GET`:
* Use the `perizer_data_curl_get` tool.
* Construct the full URL:
  ```text
  https://api.test.computesphere.com/api/v1 + path from `RSS Read`
  ```
* Include:
  * All required path and query parameters.
  * `Authorization` header with the exact token from Redis..
####  If `POST`:
* Use the `perizer_data_curl_post` tool.
* Construct the full URL the same way.
* Include:
  * Required path parameters.
  * JSON request body (as defined in the docs).
  * `Authorization` header with the exact token from Redis.

####  If `PUT`:
* Use the `perizer_data_curl_put` tool.
* Construct the full URL the same way.
* Include:
  * Required path parameters.
  * JSON request body (as defined in the docs).
  * `x-user-token` header with the exact token from Redis.
---
### Step 4: Return a Human-Readable Response
* **show return raw JSON**.
---
### Step 5: If No Match Found
If no relevant information is found in `RSS Read`, respond with:
```text
I cannot find the answer in the available resources.
```
---
###  Always Apply Logic on Every Query
* This process should be repeated for **every chat message**, including follow-up messages.
* Always fetch the **latest method** and **match from `RSS Read`**, even if the query seems repetitive.
* `x-user-token:` dont include text in token and also Bearer. 
* Always Give suggestion after every request
* Dont Assume anything ,instead Call a tool for response.
---
"""

    async def process_chat_message(self, message: str, session_id: str) -> str:
        try:
            # Step 1: Get token from Redis
            token_response = await self.mcp_client.call_tool("redis_get_token", key=session_id)
            token_data = json.loads(token_response)

            if "error" in token_data:
                return f"❌ **Authentication Error**\n\nError retrieving authentication token: {token_data['error']}\n\nPlease make sure your session ID '{session_id}' is valid and has a token stored in Redis."

            token = token_data.get("token")
            if not token:
                return "❌ **Authentication Error**\n\nAuthentication token not found. Please check your session."

            print(f"✅ Token retrieved: {token}")

            # Step 2: Load RSS feed data
            rss_response = await self.mcp_client.call_tool("rss_feed_read")
            rss_data = json.loads(rss_response)
            if "error" in rss_data:
                return f"❌ **RSS Error**\n\nError loading RSS data: {rss_data['error']}"

            print(f"✅ RSS data loaded: {len(rss_data.get('endpoints', []))} endpoints")

            # Step 3: Match message to endpoint
            best_match = None
            highest_score = 0
            message_lower = message.lower()
            
            for endpoint in rss_data.get("endpoints", []):
                score = 0
                for keyword in endpoint.get("keywords", []):
                    if keyword.lower() in message_lower:
                        score += 1
                
                if score > highest_score:
                    highest_score = score
                    best_match = endpoint

            if not best_match:
                return f"❌ **No Matching Endpoint**\n\nI cannot find the answer in the available resources.\n\n**Available endpoints:** {len(rss_data.get('endpoints', []))}\n\n**Suggestion:** Try asking about users, notifications, messages, or other available API endpoints."

            print(f"✅ Matched endpoint: {best_match['method']} {best_match['path']} (score: {highest_score})")

            # Step 4: Execute the actual API call
            BASE_API_URL = "https://api.test.computesphere.com"
            
            # Check if path already includes /api/v1, if so don't add it again
            if best_match['path'].startswith('/api/v1'):
                full_url = BASE_API_URL + best_match['path']
            else:
                full_url = BASE_API_URL + "/api/v1" + best_match['path']
            
            print(f"🔄 Making {best_match['method']} request to: {full_url}")

            if best_match['method'] == 'GET':
                api_response = await self.mcp_client.call_tool(
                    "perizer_data_curl_get",
                    url=full_url,
                    parameters2_Value=token
                )
            elif best_match['method'] == 'POST':
                api_response = await self.mcp_client.call_tool(
                    "perizer_data_curl_post",
                    url=full_url,
                    parameters4_Value=token
                )
            elif best_match['method'] == 'PUT':
                api_response = await self.mcp_client.call_tool(
                    "perizer_data_curl_put",
                    url=full_url,
                    parameters4_Value=token,
                    JSON={}
                )
            else:
                return f"❌ **Unsupported Method**\n\nHTTP method '{best_match['method']}' is not supported."

            # Step 5: Parse and display results
            api_data = json.loads(api_response)
            
            if api_data.get("success"):
                response_text = f"✅ **API Call Successful**\n\n"
                response_text += f"**Method:** {best_match['method']}\n"
                response_text += f"**URL:** {full_url}\n"
                response_text += f"**Status Code:** {api_data.get('status_code')}\n"
                response_text += f"**Endpoint:** {best_match['path']}\n\n"
                
                response_text += f"**Raw API Response:**\n```json\n{json.dumps(api_data.get('data'), indent=2)}\n```\n\n"
                
                formatted_response = self._format_response_for_human(api_data.get('data', {}))
                response_text += f"**Human-Readable Result:**\n{formatted_response}\n\n"
                response_text += f"**Suggestion:** You can ask about other endpoints or request specific actions."
                return response_text
            else:
                return f"❌ **API Call Failed**\n\nError: {api_data.get('error', 'Unknown error')}\n\nURL: {full_url}\n\n**Suggestion:** Please check your session token or try a different request."

        except Exception as e:
            return f"❌ **Processing Error**\n\nError: {str(e)}"

    def _format_response_for_human(self, data: Any) -> str:
        """Convert API response data to human-readable format"""
        if isinstance(data, dict):
            if not data:
                return "No data found."
            formatted = "Here's the information I found:\n"
            for k, v in data.items():
                formatted += f"• {k}: {json.dumps(v, indent=2)}\n"
            return formatted
        elif isinstance(data, list):
            if not data:
                return "No items found."
            formatted = f"Found {len(data)} items:\n"
            for i, item in enumerate(data[:5], 1):
                formatted += f"{i}. {json.dumps(item, indent=2)}\n"
            if len(data) > 5:
                formatted += f"... and {len(data) - 5} more items."
            return formatted
        return str(data)


class ChatInterface:
    """Simple chat interface for the AI agent."""

    def __init__(self):
        self.ai_model = genai.GenerativeModel("gemini-1.5-flash")
        self.agent: AIAgent | None = None

    async def start_chat(self):
        print("AI Agent Chat Interface")
        print("Type 'quit' to exit, 'health' to check system status")
        print("Type 'tools' to list available tools, 'curl-tools' to list via curl")
        print("-" * 50)
        print("Note: Make sure the MCP server is running (python3 server.py)")
        print("-" * 50)

        session_id = input("Enter your session ID: ").strip()

        try:
            async with MCPClient() as mcp:
                self.agent = AIAgent(mcp, self.ai_model)

                while True:
                    try:
                        user_input = input(f"[{session_id}] You: ").strip()
                        if user_input.lower() == "quit":
                            print("Exiting...")
                            break
                        elif user_input.lower() == "health":
                            health_status = await mcp.call_tool("health_check")
                            print(f"System Status: {health_status}")
                            continue
                        elif user_input.lower() == "tools":
                            tools_list = await mcp.list_tools()
                            tools_data = json.loads(tools_list)
                            print("Available MCP Tools:")
                            if "tools" in tools_data:
                                for tool in tools_data["tools"]:
                                    print(f"  • {tool['name']}: {tool['description']}")
                            else:
                                print(f"  Error: {tools_data}")
                            continue
                        elif user_input.lower() == "curl-tools":
                            tools_list = await mcp.list_tools_curl()
                            tools_data = json.loads(tools_list)
                            print("Available MCP Tools (via curl):")
                            if "tools" in tools_data:
                                for tool in tools_data["tools"]:
                                    print(f"  • {tool['name']}: {tool['description']}")
                            else:
                                print(f"  Error: {tools_data}")
                            continue
                        elif not user_input:
                            continue

                        print("Agent: Processing your request...")
                        response = await self.agent.process_chat_message(user_input, session_id)
                        print(f"Agent: {response}")

                    except KeyboardInterrupt:
                        print("\nGoodbye!")
                        break
                    except Exception as e:
                        print(f"Error: {e}")
        except Exception as e:
            print(f"Failed to start chat interface: {e}")
            print("Please ensure the MCP server is running and try again.")


if __name__ == "__main__":
    # Replace with your actual API key
    genai.configure(api_key=os.getenv("GENAI_API_KEY"))
    interface = ChatInterface()
    asyncio.run(interface.start_chat())

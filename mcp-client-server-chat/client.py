# ====================================
# ai_agent_client.py - The AI Agent (replaces your first n8n workflow)
# ====================================

import asyncio
import json
from typing import Dict, Any, Optional
import google.generativeai as genai
import httpx

class MCPClient:
    """Client to communicate with MCP server tools"""
    
    def __init__(self, mcp_server_url: str = "http://localhost:8000"):
        self.mcp_server_url = mcp_server_url
        self.http_client = httpx.AsyncClient()
    
    async def call_tool(self, tool_name: str, **kwargs) -> str:
        """Call a tool on the MCP server"""
        try:
            response = await self.http_client.post(
                f"{self.mcp_server_url}/tools/{tool_name}",
                json=kwargs
            )
            response.raise_for_status()
            return response.text
        except Exception as e:
            return json.dumps({"error": f"MCP tool call failed: {str(e)}"})

class AIAgent:
    """AI Agent that processes chat messages using MCP tools"""
    
    def __init__(self, mcp_client: MCPClient, ai_client: genai):
        self.mcp_client = mcp_client
        self.ai_client = ai_client
        self.memory = {}  # Simple memory storage
        
        self.system_prompt = """
You are a helpful AI assistant designed to answer user questions based on requests.
Your responsibilities are:

### Step 1: Retrieve Authorization Token
* Always begin by connecting to the **MCP client**.
* Fetch the "x-user-token" token from **Redis**, using:
  ```text
  key = session_id
  ```
* The Redis output will contain the token (e.g., `abc123...`).
* Extract this token and use it in all subsequent HTTP requests as:
  ```http
  x-user-token: <token>
  ```
Important:
  The x-user-token received from Redis must be used exactly as returned when sent in the header for API requests.
  Extract the full token string (e.g., abc123...).
  Store in memory as: session_id = abc123...

### Step 2: Match Message with RSS Read
* Always check if the **chat message matches any path in RSS Read**.
* If found, identify the corresponding HTTP method: `GET`, `POST`, or `PUT`.

### Step 3: Make the API Request
Use the appropriate tool and follow these rules based on the HTTP method:
#### If `GET`:
* Use the `perizer_data_curl_get` tool.
* Construct the full URL:
  ```text
  https://api.test.computesphere.com/api/v1 + path from RSS Read
  ```
* Include all required path and query parameters.
* Include Authorization header with the exact token from Redis.

#### If `POST`:
* Use the `perizer_data_curl_post` tool.
* Construct the full URL the same way.
* Include required path parameters.
* Include JSON request body (as defined in the docs).
* Include Authorization header with the exact token from Redis.

#### If `PUT`:
* Use the `perizer_data_curl_put` tool.
* Construct the full URL the same way.
* Include required path parameters.
* Include JSON request body (as defined in the docs).
* Include x-user-token header with the exact token from Redis.

### Step 4: Return a Human-Readable Response
* Convert **all HTTP responses** into **simple, clear, human-readable output**.
* **Do not return raw JSON**.

### Step 5: If No Match Found
If no relevant information is found in RSS Read, respond with:
```text
I cannot find the answer in the available resources.
```

### Always Apply Logic on Every Query
* This process should be repeated for **every chat message**, including follow-up messages.
* Always fetch the **latest method** and **match from RSS Read**, even if the query seems repetitive.
* `x-user-token:` dont include text in token and also Bearer.
* Always Give suggestion after every request
"""

    async def process_chat_message(self, message: str, session_id: str) -> str:
        """Process a chat message using the MCP tools"""
        try:
            # Step 1: Get token from Redis
            token_response = await self.mcp_client.call_tool("redis_get_token", key=session_id)
            token_data = json.loads(token_response)
            
            if "error" in token_data:
                return f"Error retrieving authentication token: {token_data['error']}"
            
            token = token_data.get("token")
            if not token:
                return "Authentication token not found. Please check your session."
            
            # Store token in memory
            self.memory[session_id] = token
            
            # Step 2: Load RSS feed data
            rss_response = await self.mcp_client.call_tool("rss_feed_read")
            rss_data = json.loads(rss_response)
            
            if "error" in rss_data:
                return f"Error loading RSS data: {rss_data['error']}"
            
            # Step 3: Use AI to determine the appropriate API call
            ai_response = await self._get_ai_response(message, token, rss_data, session_id)
            
            return ai_response
            
        except Exception as e:
            return f"Error processing message: {str(e)}"
    
    async def _get_ai_response(self, user_message: str, token: str, rss_data: dict, session_id: str) -> str:
        """Get AI response with tool calling capabilities"""
        
        # Define available tools for the AI
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "perizer_data_curl_get",
                    "description": "Make HTTP GET request to API",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "Full URL for the GET request"},
                            "parameters2_Value": {"type": "string", "description": "Authentication token"}
                        },
                        "required": ["url", "parameters2_Value"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "perizer_data_curl_post",
                    "description": "Make HTTP POST request to API",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "Full URL for the POST request"},
                            "parameters4_Value": {"type": "string", "description": "Authentication token"},
                            "parameters0_Name": {"type": "string", "description": "First body parameter name"},
                            "parameters0_Value": {"type": "string", "description": "First body parameter value"},
                            "parameters1_Name": {"type": "string", "description": "Second body parameter name"},
                            "parameters1_Value": {"type": "string", "description": "Second body parameter value"}
                        },
                        "required": ["url", "parameters4_Value"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "perizer_data_curl_put",
                    "description": "Make HTTP PUT request to API",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "Full URL for the PUT request"},
                            "parameters4_Value": {"type": "string", "description": "Authentication token"},
                            "JSON": {"type": "object", "description": "JSON body for the PUT request"}
                        },
                        "required": ["url", "parameters4_Value", "JSON"]
                    }
                }
            }
        ]
        
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"""
User message: {user_message}
Session ID: {session_id}
Available token: {token}
RSS endpoints data: {json.dumps(rss_data, indent=2)}

Please process this request following the steps in your instructions.
"""}
        ]
        
        # Call AI with tools
        response = await self.ai_client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            tools=tools,
            tool_choice="auto"
        )
        
        # Handle tool calls
        if response.choices[0].message.tool_calls:
            for tool_call in response.choices[0].message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                # Call the appropriate MCP tool
                tool_result = await self.mcp_client.call_tool(function_name, **function_args)
                
                # Parse the result and format for human readability
                try:
                    result_data = json.loads(tool_result)
                    if "error" in result_data:
                        return f"Error: {result_data['error']}\n\n💡 Suggestions:\n- Check your authentication\n- Verify the API endpoint\n- Try a different request format"
                    
                    # Format successful response
                    if "data" in result_data:
                        formatted_response = self._format_response_for_human(result_data["data"])
                        return f"{formatted_response}\n\n💡 Suggestions:\n- Try asking about other endpoints\n- Check your data status\n- Update your configuration"
                    else:
                        return f"Request completed successfully.\n\n💡 Suggestions:\n- Try asking about other endpoints\n- Check your data status\n- Update your configuration"
                        
                except json.JSONDecodeError:
                    return f"Response: {tool_result}\n\n💡 Suggestions:\n- Try asking about other endpoints\n- Check your data status\n- Update your configuration"
        
        # If no tools were called, return the AI's direct response
        ai_message = response.choices[0].message.content
        if "cannot find" in ai_message.lower():
            return "I cannot find the answer in the available resources."
        
        return ai_message
    
    def _format_response_for_human(self, data: Any) -> str:
        """Convert API response data to human-readable format"""
        if isinstance(data, dict):
            if len(data) == 0:
                return "No data found."
            
            # Format dictionary data
            formatted = "Here's the information I found:\n"
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    formatted += f"• {key}: {json.dumps(value, indent=2)}\n"
                else:
                    formatted += f"• {key}: {value}\n"
            return formatted
            
        elif isinstance(data, list):
            if len(data) == 0:
                return "No items found."
            
            formatted = f"Found {len(data)} items:\n"
            for i, item in enumerate(data[:5], 1):  # Limit to first 5 items
                formatted += f"{i}. {json.dumps(item, indent=2)}\n"
            
            if len(data) > 5:
                formatted += f"... and {len(data) - 5} more items."
            
            return formatted
        
        else:
            return str(data)

# Chat Interface
class ChatInterface:
    """Simple chat interface for the AI agent"""
    
    def __init__(self):
        self.mcp_client = MCPClient()
        # Initialize OpenAI client - you'll need to add your API key
        self.ai_client = genai.configure(api_key="AIzaSyBha_fpW1KlJjcRPUbi3m4DalIUqd-3V1Y")
        self.agent = AIAgent(self.mcp_client, self.ai_client)
    
    async def start_chat(self):
        """Start interactive chat session"""
        print("AI Agent Chat Interface")
        print("Type 'quit' to exit, 'health' to check system status")
        print("-" * 50)
        
        session_id = input("Enter your session ID: ").strip()
        
        while True:
            try:
                user_input = input(f"\n[{session_id}] You: ").strip()
                
                if user_input.lower() == 'quit':
                    break
                elif user_input.lower() == 'health':
                    # Health check
                    health_status = await self.mcp_client.call_tool("rss_feed_read")
                    print(f"System Status: {health_status}")
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

# Main execution
if __name__ == "__main__":
    # For running the chat interface
    interface = ChatInterface()
    asyncio.run(interface.start_chat())
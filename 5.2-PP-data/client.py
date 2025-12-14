
"""
Strands Agents Client with MCP Server Integration
This client uses Strands Agents with OpenAI integration to communicate with the MCP server.
"""

import base64
import logging
# Configure the root strands logger
logging.getLogger("strands").setLevel(logging.DEBUG)
# Add a handler to see the logs
logging.basicConfig(
    format="%(levelname)s | %(name)s | %(message)s",
    handlers=[logging.StreamHandler()]
)

from multiprocessing.util import get_logger
import os
import asyncio
import json
from typing import Optional, Dict, Any

from dotenv import load_dotenv
load_dotenv()

# Strands Agents imports
from strands import Agent
from strands.models.openai import OpenAIModel
from strands.tools.mcp import MCPClient
from strands_tools import mem0_memory, use_llm
from mcp import stdio_client, StdioServerParameters


# --- Strands Observability: Metrics, Logging, Tracing ---
try:
    from strands.telemetry import StrandsTelemetry
    import os
    langfuse_public = os.getenv("LANGFUSE_PUBLIC_KEY")
    langfuse_secret = os.getenv("LANGFUSE_SECRET_KEY")
    langfuse_host = os.getenv("LANGFUSE_HOST")
    if not (langfuse_public and langfuse_secret and langfuse_host):
        raise EnvironmentError("Langfuse credentials or host missing in environment. Check your .env file.")
    import base64
    auth = base64.b64encode(f"{langfuse_public}:{langfuse_secret}".encode()).decode()
    os.environ["OTEL_EXPORTER_OTLP_ENDPOINT"] = langfuse_host.rstrip('"') + "/api/public/otel"
    os.environ["OTEL_EXPORTER_OTLP_HEADERS"] = f"Authorization=Basic {auth}"

    strands_telemetry = StrandsTelemetry()
    strands_telemetry.setup_otlp_exporter() 
         # Send traces to OTLP endpoint
    # Set up logger and metrics
    logger = logging.getLogger("computesphere.agent")
    # Example metric: count agent initializations and chats
    if hasattr(strands_telemetry, "counter"):
        agent_init_counter = strands_telemetry.counter("agent_initializations", "Number of agent initializations")
        chat_counter = strands_telemetry.counter("agent_chats", "Number of agent chat calls")
    else:
        logger.warning("StrandsTelemetry does not support 'counter' method. Metrics will be disabled.")
        agent_init_counter = None
        chat_counter = None
except ImportError:
    logger = None
    agent_init_counter = None
    chat_counter = None
    pass  # If not available, skip observability

class ComputesphereAgent:
    """
    A Strands Agent client that communicates with the Computesphere MCP server with memory capabilities.
    """
    
    def __init__(self, google_api_key: Optional[str] = None, session_id: Optional[str] = None, enable_memory: bool = True):
        """
        Initialize the Computesphere Agent.
        
        Args:
            google_api_key: Google API key for the Gemini model
            session_id: Session ID for MCP server authentication
            enable_memory: Whether to enable conversation memory
        """
        self.google_api_key = google_api_key or os.getenv('GOOGLE_API_KEY')
        self.session_id = session_id or os.getenv('SESSION_ID', 'default-session')
        self.enable_memory = enable_memory
        self.user_id = f"computesphere_user_{self.session_id}"  # Unique user ID for memory
        self.agent = None
        self.mcp_client = None
        self.conversation_history = []  # Local conversation history
        
        if not self.google_api_key:
            raise ValueError("Google API key is required. Set GOOGLE_API_KEY environment variable or pass it directly.")
    
    def setup_openai_model(self) -> OpenAIModel:
        """
        Set up the OpenAI model for the agent.
        """
        model = OpenAIModel(
            client_args={
                "api_key": self.google_api_key,
                "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
            },
            model_id="gemini-2.5-flash",
            params={
                "max_tokens": 2000,
                "temperature": 0.7,
            }
        )
        return model
    
    def setup_mcp_client(self) -> MCPClient:
        """
        Set up the MCP client to connect to the Computesphere server.
        """
        # Connect to the MCP server using stdio transport
        mcp_client = MCPClient(lambda: stdio_client(
            StdioServerParameters(
                command="python3", 
                args=["mcp_server_openapi.py"]
            )
        ))
        return mcp_client
    
    async def initialize_agent(self):
        """
        Initialize the agent with OpenAI model and MCP tools.
        """
        try:
            # Set up the OpenAI model
            model = self.setup_openai_model()
            # Set up the MCP client
            self.mcp_client = self.setup_mcp_client()
            # Start the MCP client and get tools
            self.mcp_client.start()
            tools = self.mcp_client.list_tools_sync()
            if logger:
                logger.info(f"Connected to MCP server. Available tools: {len(tools)}")
            else:
                print(f" Connected to MCP server. Available tools: {len(tools)}")
            # Prepare tools list - add memory tools if enabled
            agent_tools = list(tools)
            if self.enable_memory:
                agent_tools.extend([mem0_memory, use_llm])
                if logger:
                    logger.info("Memory tools enabled")
                else:
                    print(" Memory tools enabled")
            # Create the agent with the model and tools
            self.agent = Agent(
                model=model, 
                tools=agent_tools,
                system_prompt=f"""
                You are a helpful assistant for the Computesphere cloud platform with memory capabilities. 
                You have access to various tools to manage projects, environments, deployments, and other resources.

                IMPORTANT INSTRUCTIONS:
                1. When using MCP tools, always include sessionId='{self.session_id}' in your tool calls.
                2. Use each tool only ONCE per response - do not repeat tool calls.
                3. If a tool returns data, format it nicely and present it to the user.
                4. Be concise and avoid duplicating information.
                5. For delete operations, always ask for user confirmation first.

                MEMORY CAPABILITIES:
                - Use mem0_memory tool to store important user preferences and information
                - Always include user_id='{self.user_id}' when using memory tools
                - Store relevant context like project preferences, common tasks, user roles
                - Retrieve memories to provide personalized responses
                - Remember user's work patterns and frequently accessed resources

                You can help users with:
                - Managing projects and environments
                - Viewing deployment status and logs
                - Managing teams and users
                - Checking resource usage and billing
                - Setting up notifications and alerts
                - Remembering user preferences and work patterns
                - And much more!

                Always be helpful and provide clear, actionable responses. Use memory to make interactions more personalized and efficient.
                """,
                name="Computesphere Assistant",
                description="AI assistant for Computesphere cloud platform management with memory",
                trace_attributes={
                    "session.id": self.session_id,  # Example session ID
                    "user.id": "user-email-example@domain.com",  # Example user ID
                    "langfuse.tags": [
                        "Agent-SDK-Example",
                        "Strands-Project-Demo",
            "Observability-Tutorial"
        ]
    }
            )
            if agent_init_counter:
                agent_init_counter.inc()
            if logger:
                logger.info("Agent initialized successfully!")
            else:
                print("Agent initialized successfully!")
            return True
        except Exception as e:
            if logger:
                logger.error(f"Failed to initialize agent: {str(e)}")
            else:
                print(f"Failed to initialize agent: {str(e)}")
            return False
    
    async def chat(self, message: str, stream: bool = False) -> str:
        """
        Send a message to the agent and get a response.
        Args:
            message: The user's message/query
            stream: Whether to stream the response
        Returns:
            The agent's response
        """
        if not self.agent:
            raise RuntimeError("Agent not initialized. Call initialize_agent() first.")
        if chat_counter:
            chat_counter.inc()
        if logger:
            logger.info(f"User message: {message}")
        try:
            self.conversation_history.append({"role": "user", "content": message})
            contextual_message = f"Session ID: {self.session_id}\n\nUser Query: {message}"
            agent_result = None
            if stream:
                # Use streaming response
                response_text = ""
                async for chunk in self.agent.stream_async(contextual_message):
                    if hasattr(chunk, 'content'):
                        chunk_text = str(chunk.content)
                    elif hasattr(chunk, 'text'):
                        chunk_text = str(chunk.text)
                    else:
                        chunk_text = str(chunk)
                    print(chunk_text, end="", flush=True)
                    response_text += chunk_text
                print()  # New line after streaming
                # For streaming, metrics are not available per chunk, so skip metrics summary
            else:
                # Use regular response
                agent_result = await self.agent.invoke_async(contextual_message)
                if hasattr(agent_result, 'content'):
                    response_text = str(agent_result.content)
                elif hasattr(agent_result, 'text'):
                    response_text = str(agent_result.text)
                else:
                    response_text = str(agent_result)
            self.conversation_history.append({"role": "assistant", "content": response_text})
            if logger:
                logger.info(f"Agent response: {response_text[:200]}")
            # Print and log metrics summary if available
            if agent_result and hasattr(agent_result, 'metrics') and hasattr(agent_result.metrics, 'get_summary'):
                metrics_summary = agent_result.metrics.get_summary()
                print("\n--- Agent Execution Metrics Summary ---")
                print(json.dumps(metrics_summary, indent=2))
                if logger:
                    logger.info(f"Agent metrics summary: {metrics_summary}")
            return response_text
        except Exception as e:
            error_message = f"Error: {str(e)}"
            self.conversation_history.append({"role": "assistant", "content": error_message})
            if logger:
                logger.error(error_message)
            return error_message
    
    async def store_memory(self, content: str) -> str:
        """
        Store information in memory for later retrieval.
        Args:
            content: The information to store
        Returns:
            Confirmation message
        """
        if not self.agent or not self.enable_memory:
            return "Memory is not enabled."
        try:
            response = await self.agent.invoke_async(
                f"Remember this information: {content}",
                tools=[mem0_memory]
            )
            return "Information stored in memory successfully."
        except Exception as e:
            return f"Error storing memory: {str(e)}"
    
    async def retrieve_memories(self, query: str = None) -> str:
        """
        Retrieve relevant memories based on a query.
        Args:
            query: Optional query to find specific memories  
        Returns:
            Retrieved memories or error message
        """
        if not self.agent or not self.enable_memory:
            return "Memory is not enabled."
        try:
            if query:
                response = await self.agent.invoke_async(
                    f"What do you remember about: {query}",
                    tools=[mem0_memory]
                )
            else:
                response = await self.agent.invoke_async(
                    "What do you remember about me?",
                    tools=[mem0_memory]
                )
            if hasattr(response, 'content'):
                return str(response.content)
            elif hasattr(response, 'text'):
                return str(response.text)
            else:
                return str(response)
                
        except Exception as e:
            return f"Error retrieving memories: {str(e)}"
    
    async def list_all_memories(self) -> str:
        """
        List all stored memories.
        Returns:
            All stored memories or error message
        """
        if not self.agent or not self.enable_memory:
            return "Memory is not enabled."
        try:
            response = await self.agent.invoke_async(
                "Show me everything you remember about me",
                tools=[mem0_memory]
            )
            if hasattr(response, 'content'):
                return str(response.content)
            elif hasattr(response, 'text'):
                return str(response.text)
            else:
                return str(response)
        except Exception as e:
            return f"Error listing memories: {str(e)}"
    
    def get_conversation_history(self) -> list:
        """
        Get the current conversation history.
        
        Returns:
            List of conversation messages
        """
        return self.conversation_history.copy()
    
    def clear_conversation_history(self):
        """
        Clear the local conversation history.
        """
        self.conversation_history.clear()
        print(" Conversation history cleared.")
    
    async def chat_stream(self, message: str):
        """
        Send a message to the agent and stream the response.
        Args:
            message: The user's message/query
        Yields:
            Response chunks as they arrive
        """
        if not self.agent:
            raise RuntimeError("Agent not initialized. Call initialize_agent() first.")
        
        try:
            self.conversation_history.append({"role": "user", "content": message})
            contextual_message = f"Session ID: {self.session_id}\n\nUser Query: {message}"
            
            response_text = ""
            async for chunk in self.agent.stream_async(contextual_message):
                if hasattr(chunk, 'content'):
                    chunk_text = str(chunk.content)
                elif hasattr(chunk, 'text'):
                    chunk_text = str(chunk.text)
                else:
                    chunk_text = str(chunk)
                
                response_text += chunk_text
                yield chunk_text
            
            self.conversation_history.append({"role": "assistant", "content": response_text})
            
        except Exception as e:
            error_message = f"Error: {str(e)}"
            self.conversation_history.append({"role": "assistant", "content": error_message})
            yield error_message

    def chat_sync(self, message: str, stream: bool = False) -> str:
        """
        Synchronous version of chat method.
        """
        return asyncio.run(self.chat(message, stream))
    
    async def get_available_tools(self) -> list:
        """
        Get list of available tools from the MCP server.
        """
        if not self.mcp_client:
            raise RuntimeError("MCP client not initialized.")
        
        tools = self.mcp_client.list_tools_sync()
        return [{"name": tool.name, "description": tool.description} for tool in tools]
    
    async def close(self):
        """
        Close the MCP client connection.
        """
        if self.mcp_client:
            self.mcp_client.stop(None, None, None)
            print(" MCP client connection closed.")

class InteractiveClient:
    """
    Interactive command-line interface for the Computesphere Agent.
    """
    
    def __init__(self):
        self.agent_client = None
        self.streaming_enabled = True  # Default to streaming mode
    
    async def setup(self):
        """
        Set up the agent client.
        """
        print(" Initializing Computesphere Agent...")
        session_id = input("Enter your session ID (or press Enter for default): ").strip()
        if not session_id:
            session_id = os.getenv('SESSION_ID', 'default-session')
        enable_memory = input("Enable conversation memory? (y/n, default: y): ").strip().lower()
        enable_memory = enable_memory != 'n'
        
        # Ask about streaming preference
        enable_streaming = input("Enable text streaming? (y/n, default: y): ").strip().lower()
        self.streaming_enabled = enable_streaming != 'n'
        
        self.agent_client = ComputesphereAgent(session_id=session_id, enable_memory=enable_memory)
        
        success = await self.agent_client.initialize_agent()
        if not success:
            print(" Failed to initialize agent. Exiting.")
            return False
        
        return True
    
    async def run_interactive_mode(self):
        """
        Run the interactive chat interface.
        """
        print("\n" + "="*60)
        mode = " Streaming" if self.streaming_enabled else " Standard"
        print(f" Computesphere Agent with Memory Ready! ({mode} mode)")
        print("Type 'help' for available commands, 'quit' to exit")
        print("="*60 + "\n")
        
        while True:
            try:
                user_input = input("\nYou: ").strip()
                
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print(" Goodbye!")
                    break
                
                elif user_input.lower() == 'help':
                    await self.show_help()
                    continue
                
                elif user_input.lower() == 'tools':
                    await self.show_available_tools()
                    continue
                
                elif user_input.lower() == 'test':
                    await self.run_test_commands()
                    continue
                
                elif user_input.lower().startswith('remember '):
                    content = user_input[9:].strip()
                    if content:
                        response = await self.agent_client.store_memory(content)
                        print(f"\n {response}")
                    else:
                        print("\n Please provide content to remember.")
                    continue
                
                elif user_input.lower() in ['memories', 'list memories', 'show memories']:
                    response = await self.agent_client.list_all_memories()
                    print(f"\n Stored Memories:\n{response}")
                    continue
                
                elif user_input.lower() in ['history', 'conversation history']:
                    history = self.agent_client.get_conversation_history()
                    print(f"\n Conversation History ({len(history)} messages):")
                    for msg in history[-10:]:  # Show last 10 messages
                        role = msg['role'].capitalize()
                        content = msg['content'][:100] + "..." if len(msg['content']) > 100 else msg['content']
                        print(f"  {role}: {content}")
                    continue
                
                elif user_input.lower() in ['clear history', 'clear']:
                    self.agent_client.clear_conversation_history()
                    continue
                
                elif user_input.lower() in ['stream', 'toggle stream']:
                    self.streaming_enabled = not self.streaming_enabled
                    mode = "enabled" if self.streaming_enabled else "disabled"
                    print(f"\n Text streaming {mode}")
                    continue
                
                elif not user_input:
                    continue
                
                print("\n🤖 Agent: ", end="", flush=True)
                
                if self.streaming_enabled:
                    async for chunk in self.agent_client.chat_stream(user_input):
                        print(chunk, end="", flush=True)
                    print()  
                else:
                    response = await self.agent_client.chat(user_input, stream=False)
                    print(response)
                
            except KeyboardInterrupt:
                print("\n Goodbye!")
                break
            except Exception as e:
                print(f"\n Error: {str(e)}")
    
    async def show_help(self):
        """
        Show available commands.
        """
        help_text = """
        Available Commands:
        - help: Show this help message
        - tools: List available MCP tools
        - test: Run some test commands
        - stream: Toggle text streaming mode
        - quit/exit/bye: Exit the application

        Memory Commands:
        - remember <info>: Store information in memory
        - memories: List all stored memories
        - history: Show conversation history
        - clear: Clear conversation history

        Example queries:
        - "List all my projects"
        - "Show project details for project ID abc123"
        - "Get account overview"
        - "Show deployment status"
        - "List recent activity logs"
        - "Get resource usage information"

        Memory examples:
        - "remember I prefer staging environments for testing"
        - "remember my main project is project-abc123"
        - "What do you remember about my preferences?"

        Streaming Mode:
        - Responses are displayed in real-time as they're generated
        - Use 'stream' command to toggle streaming on/off
"""
        print(help_text)
    
    async def show_available_tools(self):
        """
        Show available MCP tools.
        """
        try:
            tools = await self.agent_client.get_available_tools()
            print(f"\n🔧 Available Tools ({len(tools)}):")
            for i, tool in enumerate(tools, 1):
                print(f"{i:2d}. {tool['name']}: {tool['description']}")
        except Exception as e:
            print(f" Error getting tools: {str(e)}")
    
    async def run_test_commands(self):
        """
        Run some test commands to verify functionality.
        """
        test_commands = [
            "Test the API connection",
            "Get account overview",
            "List all projects"
        ]
        
        print("\n🧪 Running test commands...")
        
        for i, command in enumerate(test_commands, 1):
            print(f"\n{i}. Testing: {command}")
            try:
                response = await self.agent_client.chat(command)
                print(f" Response: {response[:200]}..." if len(response) > 200 else f" Response: {response}")
            except Exception as e:
                print(f" Error: {str(e)}")
    
    async def cleanup(self):
        """
        Clean up resources.
        """
        if self.agent_client:
            await self.agent_client.close()

async def main():
    """
    Main function to run the interactive client.
    """
    client = InteractiveClient()
    try:
        if not await client.setup():
            return
        await client.run_interactive_mode()   
    finally:
        # Cleanup
        await client.cleanup()
if __name__ == "__main__":
    asyncio.run(main())
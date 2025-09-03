"""
Strands Agents Client with MCP Server Integration
This client uses Strands Agents with OpenAI integration to communicate with the MCP server.
"""

import os
import asyncio
import json
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Strands Agents imports
from strands import Agent
from strands.models.openai import OpenAIModel
from strands.tools.mcp import MCPClient
from mcp import stdio_client, StdioServerParameters

# Load environment variables
load_dotenv()

class ComputesphereAgent:
    """
    A Strands Agent client that communicates with the Computesphere MCP server.
    """
    
    def __init__(self, google_api_key: Optional[str] = None, session_id: Optional[str] = None):
        """
        Initialize the Computesphere Agent.
        
        Args:
            google_api_key: Google API key for the Gemini model
            session_id: Session ID for MCP server authentication
        """
        self.google_api_key = google_api_key or os.getenv('GOOGLE_API_KEY')
        self.session_id = session_id or os.getenv('SESSION_ID', 'default-session')
        self.agent = None
        self.mcp_client = None
        
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
            
            print(f"✅ Connected to MCP server. Available tools: {len(tools)}")
            
            # Create the agent with the model and MCP tools
            self.agent = Agent(
                model=model, 
                tools=tools,
                system_prompt=f"""
                You are a helpful assistant for the Computesphere cloud platform. 
                You have access to various tools to manage projects, environments, deployments, and other resources.
                
                Important: When using MCP tools, always include sessionId='{self.session_id}' in your tool calls.
                
                You can help users with:
                - Managing projects and environments
                - Viewing deployment status and logs
                - Managing teams and users
                - Checking resource usage and billing
                - Setting up notifications and alerts
                - And much more!
                
                Always be helpful and provide clear, actionable responses.
                """,
                name="Computesphere Assistant",
                description="AI assistant for Computesphere cloud platform management"
            )
            
            print("✅ Agent initialized successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize agent: {str(e)}")
            return False
    
    async def chat(self, message: str) -> str:
        """
        Send a message to the agent and get a response.
        
        Args:
            message: The user's message/query
            
        Returns:
            The agent's response
        """
        if not self.agent:
            raise RuntimeError("Agent not initialized. Call initialize_agent() first.")
        
        try:
            # Add session context to the message
            contextual_message = f"Session ID: {self.session_id}\n\nUser Query: {message}"
            
            response = await self.agent.invoke_async(contextual_message)
            return response
            
        except Exception as e:
            return f"Error: {str(e)}"
    
    def chat_sync(self, message: str) -> str:
        """
        Synchronous version of chat method.
        """
        return asyncio.run(self.chat(message))
    
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
            print("✅ MCP client connection closed.")

class InteractiveClient:
    """
    Interactive command-line interface for the Computesphere Agent.
    """
    
    def __init__(self):
        self.agent_client = None
    
    async def setup(self):
        """
        Set up the agent client.
        """
        print("🚀 Initializing Computesphere Agent...")
        
        # Get session ID from user or environment
        session_id = input("Enter your session ID (or press Enter for default): ").strip()
        if not session_id:
            session_id = os.getenv('SESSION_ID', 'default-session')
        
        self.agent_client = ComputesphereAgent(session_id=session_id)
        
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
        print(" Computesphere Agent Ready!")
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
                
                elif not user_input:
                    continue
                
                print("\n Agent: ", end="", flush=True)
                response = await self.agent_client.chat(user_input)
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
- quit/exit/bye: Exit the application

 Example queries:
- "List all my projects"
- "Show project details for project ID abc123"
- "Get account overview"
- "Show deployment status"
- "List recent activity logs"
- "Get resource usage information"
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
        # Setup the agent
        if not await client.setup():
            return
        
        # Run interactive mode
        await client.run_interactive_mode()
        
    finally:
        # Cleanup
        await client.cleanup()

# Example usage functions
async def example_basic_usage():
    """
    Example of basic usage without interactive mode.
    """
    print("📚 Basic Usage Example")
    
    # Initialize the agent
    agent = ComputesphereAgent(session_id="example-session")
    
    try:
        # Initialize
        await agent.initialize_agent()
        
        # Example queries
        queries = [
            "What tools are available?",
            "Test the API connection",
            "Get my account overview"
        ]
        
        for query in queries:
            print(f"\n🔍 Query: {query}")
            response = await agent.chat(query)
            print(f" Response: {response}")
            
    finally:
        await agent.close()

async def example_project_management():
    """
    Example focused on project management tasks.
    """
    print("📁 Project Management Example")
    
    agent = ComputesphereAgent(session_id="project-session")
    
    try:
        await agent.initialize_agent()
        
        # Project management queries
        queries = [
            "List all my projects",
            "Show me the account overview",
            "Get resource usage information",
            "List recent activity logs"
        ]
        
        for query in queries:
            print(f"\n🔍 Query: {query}")
            response = await agent.chat(query)
            print(f" Response: {response[:500]}...")
            
    finally:
        await agent.close()

if __name__ == "__main__":
    print("🌟 Computesphere Strands Agent Client")
    print("Choose an option:")
    print("1. Interactive mode (default)")
    print("2. Basic usage example")
    print("3. Project management example")
    
    choice = input("\nEnter your choice (1-3, default=1): ").strip()
    
    if choice == "2":
        asyncio.run(example_basic_usage())
    elif choice == "3":
        asyncio.run(example_project_management())
    else:
        asyncio.run(main())
from strands import Agent
from strands.multiagent.a2a import A2AServer
from strands.tools.mcp import MCPClient
from mcp import stdio_client, StdioServerParameters
from strands.models.openai import OpenAIModel
from dotenv import load_dotenv
import os
from typing import Optional, Dict, Any

load_dotenv()

class MathAgentWithMemory:
    """
    A Strands Agent client that communicates with the mcp with memory capabilities.
    """
    def __init__(self, google_api_key: Optional[str] = None, session_id: Optional[str] = None, enable_memory: bool = True):
        """
        Initialize the Math Agent.
        
        Args:
            google_api_key: Google API key for the Gemini model
            session_id: Session ID for MCP server authentication
            enable_memory: Whether to enable conversation memory
        """
        self.google_api_key = google_api_key or os.getenv('GOOGLE_API_KEY')
        self.session_id = session_id or os.getenv('SESSION_ID', 'default-session')
        self.enable_memory = enable_memory
        self.user_id = f"math_user_{self.session_id}"  # Unique user ID for memory
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

# Connect to the local math MCP server
mcp_client = MCPClient(lambda: stdio_client(
    StdioServerParameters(command="python", args=["./list-of-mcp/math_mcp_server.py"])
))

with mcp_client:
    model = MathAgentWithMemory().setup_openai_model()
    tools = mcp_client.list_tools_sync()
    math_agent = Agent(name="math_agent",
                       model=model,
                       description="A math agent that exposes math tools via MCP.",
                       tools=tools)

    # Expose via A2A
    server = A2AServer(agent=math_agent, port=9001)
    server.serve()

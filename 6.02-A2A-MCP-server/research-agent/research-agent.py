from strands import Agent
from strands.multiagent.a2a import A2AServer
from strands.tools.mcp import MCPClient
from mcp import stdio_client, StdioServerParameters
from strands.models.openai import OpenAIModel
from dotenv import load_dotenv
import os
import asyncio
import logging
from typing import Optional, Dict, Any

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ResearchAgentWithMemory:
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
        self.user_id = f"research_user_{self.session_id}"  # Unique user ID for memory
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

# Connect to the local search MCP server
try:
    mcp_client_1 = MCPClient(lambda: stdio_client(
        StdioServerParameters(command="python", args=["./list-of-mcp/search_mcp_server.py"])
    ))
    mcp_client = MCPClient(lambda: stdio_client(
        StdioServerParameters(command="python", args=["./list-of-mcp/search_mcp_google_notifier.py"])
    ))

    with mcp_client, mcp_client_1:
        logger.info("Connected to search MCP server")
        model = ResearchAgentWithMemory().setup_openai_model()
        tools = mcp_client.list_tools_sync() + mcp_client_1.list_tools_sync()
        research_agent = Agent(name="research_agent",
                               model=model,
                               description="A research agent that exposes search tools via MCP and it does not require search url, only research words.", 
                               tools=tools)

        logger.info("Research agent initialized, starting A2A server on port 9002")
        # Expose via A2A
        server = A2AServer(agent=research_agent, port=9002)
        
        # Start the server with health check
        logger.info("Starting A2A server with health check...")
        server.serve()
        
except Exception as e:
    logger.error(f"Failed to start research agent: {e}")
    raise

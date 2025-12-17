import asyncio
import os
import logging
from typing import Any, Optional
from strands import Agent
from strands_tools.a2a_client import A2AClientToolProvider
from dotenv import load_dotenv
from strands.models.openai import OpenAIModel
import nest_asyncio
from config import get_config
from agent_registry_service import create_registry_app
import uvicorn
import threading

load_dotenv()
nest_asyncio.apply()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration
config = get_config()
urls = config.agent.urls

if not urls:
    logger.info(
        "No A2A agent URLs pre-configured. Use /register endpoint to add agents dynamically."
    )

class DeepSeekOpenAIModel(OpenAIModel):
    """OpenAIModel variant that flattens text-only messages for DeepSeek."""

    @staticmethod
    def _flatten_text_content(payload: dict[str, Any]) -> None:
        """Mutate the payload so pure-text lists collapse into a single string."""

        for message in payload.get("messages", []):
            content = message.get("content")
            if isinstance(content, list) and content and all(
                isinstance(part, dict) and part.get("type") == "text" and "text" in part
                for part in content
            ):
                message["content"] = "\n\n".join(part["text"] for part in content)

    def format_request(self, *args, **kwargs):
        request = super().format_request(*args, **kwargs)
        self._flatten_text_content(request)
        return request


class OrchestratorAgentWithMemory:
    """
    A Strands Agent client that communicates with the mcp with memory capabilities.
    """
    def __init__(self, mistral_api_key: Optional[str] = None, session_id: Optional[str] = None, enable_memory: bool = True):
        """
        Initialize the Orchestrator Agent.

        Args:
            mistral_api_key: Mistral API key for the Mistral model
            session_id: Session ID for MCP server authentication
            enable_memory: Whether to enable conversation memory
        """
        self.session_id = session_id or os.getenv('SESSION_ID', 'default-session')
        self.enable_memory = enable_memory
        self.user_id = f"research_user_{self.session_id}"  # Unique user ID for memory
        self.agent = None
        self.mcp_client = None
        self.conversation_history = []  # Local conversation history

    def setup_openai_model(self) -> OpenAIModel:
        """
        Set up the OpenAI model for the agent.
        """
        model = OpenAIModel(
            client_args={
                "api_key": os.getenv("GOOGLE_API_KEY"),
                "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
            },
            model_id="gemini-2.5-flash",
            params={
                "max_tokens": 2000,
                "temperature": 0.7,
            }
        )
        return model

    def setup_deepseek_model(self) -> OpenAIModel:
        """
        Set up the DeepSeek model for the agent using configuration.
        """
        logger.info(f"Orchestrator DeepSeek base_url={config.model.base_url} timeout={config.model.timeout}")

        model = DeepSeekOpenAIModel(
            client_args={
                "api_key": config.model.api_key,
                "base_url": config.model.base_url,
                "timeout": config.model.timeout,
            },
            model_id=config.model.model_id,
            params={
                "max_tokens": config.model.max_tokens,
                "temperature": config.model.temperature,
            }
        )
        return model


async def get_async_input(prompt: str) -> str:
    """Get input asynchronously to avoid blocking the event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, input, prompt)


def start_registry_service(host: str = "127.0.0.1", port: int = 8000):
    """Start the agent registry service in a background thread."""
    registry_app = create_registry_app(config)
    
    def run_server():
        # Create a new event loop for this thread to avoid nest_asyncio conflicts
        new_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(new_loop)
        
        logger.info(f"Starting Agent Registry API on {host}:{port}")
        logger.info("Register agents via: POST http://{host}:{port}/register")
        logger.info("List agents via: GET http://{host}:{port}/agents")
        
        try:
            config_obj = uvicorn.Config(
                app=registry_app,
                host=host,
                port=port,
                log_level="info",
                use_colors=False
            )
            server = uvicorn.Server(config_obj)
            new_loop.run_until_complete(server.serve())
        finally:
            new_loop.close()
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    logger.info(f"Registry service started on http://{host}:{port}")


async def main():
    try:
        # Start the registry service in background
        registry_host = os.getenv("ORCHESTRATOR_REGISTRY_HOST", "127.0.0.1")
        registry_port = int(os.getenv("ORCHESTRATOR_REGISTRY_PORT", "8000"))
        start_registry_service(registry_host, registry_port)
        
        # Wait for registry to start
        await asyncio.sleep(2)
        
        # Use dynamically registered agents
        urls = config.agent.urls
        
        if urls:
            provider = A2AClientToolProvider(known_agent_urls=urls)
            agents = await provider._list_discovered_agents()
            logger.info(f"Discovered agents: {agents}")
            await asyncio.sleep(2)

            # Dynamically build agent/server list for the system prompt
            agent_lines = []
            for agent in agents['agents']:
                name = agent.get('name', 'unknown_agent')
                url = agent.get('url', 'unknown_url')
                skills = ', '.join([s.get('name', '') for s in agent.get('skills', [])])
                desc = agent.get('description', '')
                agent_lines.append(f"- {name} at {url} ({skills}) {desc}")
            agent_list_str = '\n'.join(agent_lines)
        else:
            logger.warning("No agents registered yet. Register agents via the /register endpoint.")
            agent_list_str = "No agents currently available. Register agents using the registry API."
            provider = None

        orchestrator_config = OrchestratorAgentWithMemory(
            mistral_api_key=os.getenv("MISTRAL_API_KEY"),
            session_id=config.agent.session_id,
            enable_memory=config.agent.enable_memory,
        )

        if provider:
            orchestrator = Agent(
                name="orchestrator",
                model=orchestrator_config.setup_deepseek_model(),
                system_prompt=(
                    "You are an orchestrator agent in a multi-agent system. "
                    "You have access to the following specialized agents and their MCP servers: \n"
                    f"{agent_list_str}\n"
                    "When a user asks a question, intelligently decide which agent and tool to use based on the query intent. "
                    "Do not require the user to specify agent names or URLs. "
                    "Always use the available tools to answer user queries, with a preference for routing security requests to the CAI cybersecurity agent."
                ),
                tools=provider.tools
            )
            print("Type your request (or 'exit' to quit):")
            while True:
                try:
                    user_input = await get_async_input("> ")
                    if user_input.lower() == "exit":
                        break
                    # Send the user input to the orchestrator agent with error handling
                    try:
                        response = orchestrator(user_input)
                        orchestrator_config.conversation_history.clear()
                        print(response)
                    except Exception as e:
                        logger.error(f"Error processing request '{user_input}': {e}")
                        print(f"Sorry, I encountered an error processing your request: {e}")
                except KeyboardInterrupt:
                    logger.info("Received interrupt signal, shutting down...")
                    break
                except Exception as e:
                    logger.error(f"Unexpected error in main loop: {e}")
                    print(f"An unexpected error occurred: {e}")
        else:
            print("Registry service is running. Register agents at:")
            print(f"  POST http://{registry_host}:{registry_port}/register")
            print("Example:")
            print('  curl -X POST http://localhost:8000/register \\')
            print('    -H "Content-Type: application/json" \\')
            print('    -d \'{"name": "cybersecurity-agent", "url": "http://127.0.0.1:9003"}\'')
            print("\nPress Ctrl+C to exit.")
            while True:
                try:
                    await asyncio.sleep(1)
                except KeyboardInterrupt:
                    logger.info("Received interrupt signal, shutting down...")
                    break
                
    except Exception as e:
        logger.error(f"Failed to initialize orchestrator: {e}")
        print(f"Failed to start orchestrator: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
import asyncio
import os
import logging
from typing import Optional
from strands import Agent
from strands_tools.a2a_client import A2AClientToolProvider
from dotenv import load_dotenv
from strands.models.openai import OpenAIModel
import nest_asyncio

load_dotenv()
nest_asyncio.apply()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

session_id = os.getenv("SESSION_ID")

def _parse_url_list(raw_urls: Optional[str]) -> list[str]:
    if not raw_urls:
        return []
    parsed = [u.strip() for u in raw_urls.split(",") if u.strip()]
    return parsed


urls: list[str] = _parse_url_list(os.getenv("ORCHESTRATOR_AGENT_URLS"))
cybersecurity_agent_url = os.getenv("CYBERSECURITY_AGENT_URL")
if cybersecurity_agent_url:
    urls.append(cybersecurity_agent_url.strip())

# Remove duplicates while preserving order
urls = list(dict.fromkeys(urls))

if not urls:
    logger.warning(
        "No A2A agent URLs configured. Set ORCHESTRATOR_AGENT_URLS (comma-separated) or CYBERSECURITY_AGENT_URL."
    )

class DeepSeekOpenAIModel(OpenAIModel):
    """OpenAIModel variant that flattens text-only messages for DeepSeek."""

    def format_request(
        self,
        messages,
        tool_specs=None,
        system_prompt=None,
        tool_choice=None,
        *,
        system_prompt_content=None,
        **kwargs,
    ):
        request = super().format_request(
            messages,
            tool_specs=tool_specs,
            system_prompt=system_prompt,
            tool_choice=tool_choice,
            system_prompt_content=system_prompt_content,
            **kwargs,
        )

        for message in request.get("messages", []):
            content = message.get("content")
            if isinstance(content, list) and content and all(
                isinstance(part, dict) and part.get("type") == "text" and "text" in part
                for part in content
            ):
                message["content"] = "\n\n".join(part["text"] for part in content)

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
        Set up the OpenAI model for the agent.
        """
        base_url = (
            os.getenv("DEEPSEEK_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
            or "https://api.deepseek.ai/v1/"
        )
        timeout = float(os.getenv("ORCHESTRATOR_DEEPSEEK_TIMEOUT", "60"))

        logger.info(f"Orchestrator DeepSeek base_url={base_url} timeout={timeout}")

        model = DeepSeekOpenAIModel(
            client_args={
                "api_key": os.getenv("DEEPSEEK_API_KEY"),
                "base_url": base_url,
                "timeout": timeout,
            },
            model_id=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            params={
                "max_tokens": 2000,
                "temperature": 0.7,
            }
        )
        return model


async def get_async_input(prompt: str) -> str:
    """Get input asynchronously to avoid blocking the event loop."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, input, prompt)

async def main():
    try:
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

        orchestrator_config = OrchestratorAgentWithMemory(
            mistral_api_key=os.getenv("MISTRAL_API_KEY"),
            session_id=os.getenv("SESSION_ID"),
            enable_memory=os.getenv("ORCHESTRATOR_ENABLE_MEMORY", "false").lower() == "true",
        )

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
                
    except Exception as e:
        logger.error(f"Failed to initialize orchestrator: {e}")
        print(f"Failed to start orchestrator: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
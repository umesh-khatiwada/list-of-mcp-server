import asyncio
import logging
import os
from typing import Optional

import nest_asyncio
from dotenv import load_dotenv
from strands import Agent
from strands.models.mistral import MistralModel
from strands.models.openai import OpenAIModel
from strands_tools.a2a_client import A2AClientToolProvider

load_dotenv()
nest_asyncio.apply()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mistral_api_key = os.getenv("MISTRAL_API_KEY")
session_id = os.getenv("SESSION_ID")

urls = [
    "http://127.0.0.1:9001",  # math_agent
    "http://127.0.0.1:9002",  # research_agent
]


class OrchestratorAgentWithMemory:
    """
    A Strands Agent client that communicates with the mcp with memory capabilities.
    """

    def __init__(
        self,
        mistral_api_key: Optional[str] = None,
        session_id: Optional[str] = None,
        enable_memory: bool = True,
    ):
        """
        Initialize the Orchestrator Agent.

        Args:
            mistral_api_key: Mistral API key for the Mistral model
            session_id: Session ID for MCP server authentication
            enable_memory: Whether to enable conversation memory
        """
        self.mistral_api_key = mistral_api_key or os.getenv("MISTRAL_API_KEY")
        self.session_id = session_id or os.getenv("SESSION_ID", "default-session")
        self.enable_memory = enable_memory
        self.user_id = f"research_user_{self.session_id}"  # Unique user ID for memory
        self.agent = None
        self.mcp_client = None
        self.conversation_history = []  # Local conversation history

        if not self.mistral_api_key:
            raise ValueError(
                "MISTRAL_API_KEY key is required. Set MISTRAL_API_KEY environment variable or pass it directly."
            )

    def setup_mistral_model(self) -> MistralModel:
        """
        Set up the Mistral model for the agent.
        """
        model = MistralModel(
            api_key=os.getenv("MISTRAL_API_KEY"),
            # **model_config
            model_id="mistral-large-latest",
        )
        return model

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
            },
        )
        return model

    def setup_deepseek_model(self) -> OpenAIModel:
        """
        Set up the OpenAI model for the agent.
        """
        model = OpenAIModel(
            client_args={
                "api_key": os.getenv("DEEPSEEK_API_KEY"),
                "base_url": "https://api.deepseek.ai/v1/",  # Correct DeepSeek API base URL
            },
            model_id="deepseek-chat",
            params={
                "max_tokens": 2000,
                "temperature": 0.7,
            },
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
        for agent in agents["agents"]:
            name = agent.get("name", "unknown_agent")
            url = agent.get("url", "unknown_url")
            skills = ", ".join([s.get("name", "") for s in agent.get("skills", [])])
            desc = agent.get("description", "")
            agent_lines.append(f"- {name} at {url} ({skills}) {desc}")
        agent_list_str = "\n".join(agent_lines)

        orchestrator = Agent(
            name="orchestrator",
            model=OrchestratorAgentWithMemory(
                mistral_api_key=os.getenv("GOOGLE_API_KEY"),
                session_id=os.getenv("SESSION_ID"),
            ).setup_openai_model(),
            system_prompt=(
                "You are an orchestrator agent in a multi-agent system. "
                "You have access to the following specialized agents and their MCP servers: \n"
                f"{agent_list_str}\n"
                "When a user asks a question, intelligently decide which agent and tool to use based on the query intent. "
                "Do not require the user to specify agent names or URLs. "
                "Always use the available tools to answer user queries, and respond with clear, helpful answers."
            ),
            tools=provider.tools,
        )
        print("Using DEEPSEEK_API_KEY:", os.getenv("DEEPSEEK_API_KEY"))
        print("Type your request (or 'exit' to quit):")
        while True:
            try:
                user_input = await get_async_input("> ")
                if user_input.lower() == "exit":
                    break
                # Send the user input to the orchestrator agent with error handling
                try:
                    response = orchestrator(user_input)
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

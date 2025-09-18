import asyncio
import os
import time
from typing import Optional
from strands import Agent
from strands_tools.a2a_client import A2AClientToolProvider
from strands.models.mistral import MistralModel
from dotenv import load_dotenv


load_dotenv()

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
    def __init__(self, mistral_api_key: Optional[str] = None, session_id: Optional[str] = None, enable_memory: bool = True):
        """
        Initialize the Orchestrator Agent.

        Args:
            mistral_api_key: Mistral API key for the Mistral model
            session_id: Session ID for MCP server authentication
            enable_memory: Whether to enable conversation memory
        """
        self.mistral_api_key = mistral_api_key or os.getenv('MISTRAL_API_KEY')
        self.session_id = session_id or os.getenv('SESSION_ID', 'default-session')
        self.enable_memory = enable_memory
        self.user_id = f"research_user_{self.session_id}"  # Unique user ID for memory
        self.agent = None
        self.mcp_client = None
        self.conversation_history = []  # Local conversation history
        
        if not self.mistral_api_key:
            raise ValueError("MISTRAL_API_KEY key is required. Set MISTRAL_API_KEY environment variable or pass it directly.")
    
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



async def main():
    provider = A2AClientToolProvider(known_agent_urls=urls)
    # Use private method for agent discovery (public method not available)
    agents = await provider._list_discovered_agents()
    print("Discovered agents:", agents)
    time.sleep(2)

    # Dynamically build agent/server list for the system prompt
    agent_lines = []
    for agent in agents['agents']:
        name = agent.get('name', 'unknown_agent')
        url = agent.get('url', 'unknown_url')
        skills = ', '.join([s.get('name', '') for s in agent.get('skills', [])])
        desc = agent.get('description', '')
        agent_lines.append(f"- {name} at {url} ({skills}) {desc}")
    agent_list_str = '\n'.join(agent_lines)

    orchestrator = Agent(
        name="orchestrator",
        model=OrchestratorAgentWithMemory(
            mistral_api_key=os.getenv("MISTRAL_API_KEY"),
            session_id=os.getenv("SESSION_ID")
        ).setup_mistral_model(),
        system_prompt=(
            "You are an orchestrator agent in a multi-agent system. "
            "You have access to the following specialized agents and their MCP servers: \n"
            f"{agent_list_str}\n"
            "When a user asks a question, intelligently decide which agent and tool to use based on the query intent. "
            "Do not require the user to specify agent names or URLs. "
            "Always use the available tools to answer user queries, and respond with clear, helpful answers."
        ),
        tools=provider.tools
    )
    print("Type your request (or 'exit' to quit):")
    while True:
        user_input = input("> ")
        if user_input.lower() == "exit":
            break
        # Send the user input to the orchestrator agent
        response = orchestrator(user_input)
        print(response)

if __name__ == "__main__":
    asyncio.run(main())
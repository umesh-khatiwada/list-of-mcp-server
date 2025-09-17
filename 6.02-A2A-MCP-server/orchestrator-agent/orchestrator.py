import asyncio
import time
from strands import Agent
from strands_tools.a2a_client import A2AClientToolProvider

urls = [
    "http://localhost:9001",  # math_agent
    "http://localhost:9002",  # research_agent
]

async def main():
    provider = A2AClientToolProvider(known_agent_urls=urls)
    orchestrator = Agent(name="orchestrator", tools=provider.tools)

    # Use private method
    agents = await provider._list_discovered_agents()
    print("Discovered agents:", agents)

    time.sleep(2)


    # print(orchestrator("Ask research_agent to search 'best cloud providers'"))
    print(orchestrator("Ask math_agent to add 5 and 7"))

if __name__ == "__main__":
    asyncio.run(main())

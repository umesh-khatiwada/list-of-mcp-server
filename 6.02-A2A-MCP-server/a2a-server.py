import asyncio
import logging
from strands import Agent
from strands_tools.a2a_client import A2AClientToolProvider

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create A2A client tool provider with known agent URLs
# Assuming you have an A2A server running on 127.0.0.1:9000
# known_agent_urls is optional
provider = A2AClientToolProvider(known_agent_urls=["http://127.0.0.1:9000"])

# Create agent with A2A client tools
agent = Agent(tools=provider.tools)

# The agent can now discover and interact with A2A servers
# Standard usage
response = agent("pick an agent and make a sample call")
logger.info(response)

# Alternative Async usage
# async def main():
#     response = await agent.invoke_async("pick an agent and make a sample call")
#     logger.info(response)
# asyncio.run(main())
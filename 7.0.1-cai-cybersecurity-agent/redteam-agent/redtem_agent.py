"""
Red Team Agent - A multi-agent system for security testing and CTF challenges.

A common tactic is to break down a task into a series of smaller steps.
Each task can be performed by an agent, and the output of one agent is used as input to the next.
"""
import asyncio
import logging
import sys
import time

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from cai.sdk.agents import (
    Agent,
    OpenAIChatCompletionsModel,
    Runner,
    function_tool,
    set_tracing_disabled,
)
from cai.tools.common import run_command
from config import get_config
from openai import AsyncOpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration
config = get_config()


@function_tool
def execute_cli_command(command: str) -> str:
    return run_command(command)


ctf_agent = Agent(
    name=config.agent.name,
    description=config.agent.description,
    instructions=config.agent.system_prompt,
    tools=[
        execute_cli_command,
    ],
    model=OpenAIChatCompletionsModel(
        model=config.model.model_id,
        openai_client=AsyncOpenAI(
            api_key=config.model.api_key,
            base_url=config.model.base_url,
        ),
    ),
)


async def main():
    result = await Runner.run(ctf_agent, "List the files in the current directory?")
    print("\nAgent response:")
    print(result.final_output)


async def main_streamed():
    print("\nAgent response (streaming):")
    result = Runner.run_streamed(ctf_agent, "List the files in the current directory?")

    # Process the streaming response events
    event_count = 0
    time.time()

    # Process the streaming response
    async for event in result.stream_events():
        event_count += 1
        # Add a small delay to allow the streaming panel to update properly
        await asyncio.sleep(0.01)

        # # Print a progress indicator
        # if event_count % 10 == 0:
        #     elapsed = time.time() - start_time
        #     sys.stdout.write(f"\rProcessed {event_count} events in {elapsed:.1f} seconds...")
        #     sys.stdout.flush()

    # Clear the progress line
    sys.stdout.write("\r" + " " * 60 + "\r")
    sys.stdout.flush()


if __name__ == "__main__":
    set_tracing_disabled(True)
    asyncio.run(main())
    asyncio.run(main_streamed())

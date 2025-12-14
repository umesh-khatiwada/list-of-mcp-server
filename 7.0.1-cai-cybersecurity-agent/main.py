from cai.sdk.agents import Agent, Runner, OpenAIChatCompletionsModel
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

deepseek_client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
)

agent = Agent(
    name="Custom Agent",
    instructions="You are a Cybersecurity expert Leader",
    model=OpenAIChatCompletionsModel(
        model=os.getenv("CAI_MODEL", "deepseek/deepseek-chat"),
        openai_client=deepseek_client,
    ),
)

async def main():
    message = "Tell me about recursion in programming."
    result = await Runner.run(agent, message)
    print(result)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

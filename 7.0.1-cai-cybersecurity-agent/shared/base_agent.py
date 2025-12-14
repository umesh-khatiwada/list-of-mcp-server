import os
from typing import Optional

from cai.sdk.agents import Agent as CAIAgent, OpenAIChatCompletionsModel, Runner
from openai import AsyncOpenAI


class BaseCAIAgent:
    """Lightweight wrapper for CAI agents backed by OpenAI-compatible clients."""

    def __init__(
        self,
        *,
        agent_name: str,
        agent_type: str,
        instructions: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model_id: Optional[str] = None,
    ) -> None:
        self.agent_name = agent_name
        self.agent_type = agent_type
        self.model_id = model_id or os.getenv("CAI_MODEL", "deepseek/deepseek-chat")
        self.instructions = instructions or "You are a domain specialist operating under CAI orchestration."

        self._api_key = api_key or os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not self._api_key:
            raise RuntimeError("Set DEEPSEEK_API_KEY (or OPENAI_API_KEY) for CAI agents.")

        self._base_url = base_url or os.getenv("DEEPSEEK_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "https://api.deepseek.ai/v1/"
        self._client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)

        self._agent = CAIAgent(
            name=self.agent_name,
            instructions=self.instructions,
            model=OpenAIChatCompletionsModel(model=self.model_id, openai_client=self._client),
        )

    @property
    def agent(self) -> CAIAgent:
        return self._agent

    async def chat(self, message: str) -> str:
        run_result = await Runner.run(self._agent, message)
        return str(run_result)

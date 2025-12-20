"""Shared CAI helpers for the cybersecurity agent package."""

from __future__ import annotations

import logging
import os
from typing import Optional, Tuple

from cai.sdk.agents import Agent as CAIAgent
from cai.sdk.agents import OpenAIChatCompletionsModel, Runner
from openai import AsyncOpenAI

logger = logging.getLogger("cai.cybersecurity.base")


class BaseCAIAgent:
    """Minimal CAI agent wrapper that is self-contained within this package."""

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
        resolved_model, api_model = self._resolve_model_ids(
            model_id or os.getenv("CAI_MODEL")
        )
        self.model_id = resolved_model
        self.instructions = (
            instructions
            or "You are a domain specialist operating under CAI orchestration."
        )

        self._api_key = (
            api_key or os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
        )
        if not self._api_key:
            raise RuntimeError(
                "Set DEEPSEEK_API_KEY (or OPENAI_API_KEY) for CAI agents before starting the service."
            )

        self._base_url = (
            base_url
            or os.getenv("DEEPSEEK_BASE_URL")
            or os.getenv("OPENAI_BASE_URL")
            or "https://api.deepseek.ai/v1/"
        )
        logger.info(
            "BaseCAIAgent init model_id=%s base_url=%s", self.model_id, self._base_url
        )
        self._client = AsyncOpenAI(api_key=self._api_key, base_url=self._base_url)

        self._agent = CAIAgent(
            name=self.agent_name,
            instructions=self.instructions,
            model=OpenAIChatCompletionsModel(
                model=self.model_id,
                openai_client=self._client,
            ),
        )

        self._api_model_id = api_model

    @property
    def agent(self) -> CAIAgent:
        return self._agent

    async def chat(self, message: str) -> str:
        logger.info("CAI chat start")
        run_result = await Runner.run(self._agent, message)
        logger.info("CAI chat complete")
        return str(run_result)

    @staticmethod
    def _resolve_model_ids(configured_model: Optional[str]) -> Tuple[str, str]:
        """Return (litellm_model_id, api_model_id) based on the configured value."""

        default_litellm = "deepseek/deepseek-chat"
        default_api = "deepseek-chat"

        if not configured_model:
            return default_litellm, default_api

        model = configured_model.strip()
        if not model:
            return default_litellm, default_api

        if "/" in model:
            provider, name = model.split("/", 1)
            return model, name or default_api

        if model.startswith("deepseek"):
            return f"deepseek/{model}", model

        return model, model

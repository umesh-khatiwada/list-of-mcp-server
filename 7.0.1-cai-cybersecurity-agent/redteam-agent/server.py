"""Expose the Red Team Agent over the A2A protocol.

This enables the red team agent to be discovered and used by the orchestrator.
"""

from __future__ import annotations

import importlib.util
import logging
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from config import get_config

logger = logging.getLogger("redteam.agent.server")
logging.basicConfig(level=logging.INFO)

MODULE_PATH = Path(__file__).with_name("redtem_agent.py")
SPEC = importlib.util.spec_from_file_location("redteam_agent", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"Unable to load red team agent module from {MODULE_PATH}")

redteam_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(redteam_module)
RedTeamAgent = getattr(redteam_module, "RedTeamAgent", None)
ctf_agent = getattr(redteam_module, "ctf_agent", None)

from strands import Agent, tool
from strands.models.openai import OpenAIModel
from strands.multiagent.a2a.server import A2AServer


class DeepSeekOpenAIModel(OpenAIModel):
    """OpenAIModel subclass that flattens text content for DeepSeek compatibility."""

    @staticmethod
    def _flatten_text_content(payload: dict[str, Any]) -> None:
        """Mutate the payload so text-only lists collapse into a single string."""

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


# Load configuration
config = get_config()


@tool(name="red_team_assess", description="Run red team security assessment and CTF challenge analysis.")
async def red_team_assess(target: str) -> dict[str, Any]:
    start = time.monotonic()
    logger.info("red_team_assess start")
    
    # Use the existing ctf_agent to assess the target
    try:
        answer = ctf_agent.run(target)
        logger.info("red_team_assess complete %.2fs", time.monotonic() - start)
        return {"agent": "redteam", "assessment": answer}
    except Exception as e:
        logger.error("red_team_assess error: %s", e)
        return {"agent": "redteam", "error": str(e)}


@tool(name="exploit_discovery", description="Discover and analyze potential security exploits.")
async def exploit_discovery(context: str) -> dict[str, Any]:
    start = time.monotonic()
    logger.info("exploit_discovery start")
    
    prompt = f"Analyze the following security context and identify potential exploits:\n\n{context}"
    
    try:
        answer = ctf_agent.run(prompt)
        logger.info("exploit_discovery complete %.2fs", time.monotonic() - start)
        return {"agent": "redteam", "exploits": answer}
    except Exception as e:
        logger.error("exploit_discovery error: %s", e)
        return {"agent": "redteam", "error": str(e)}


@tool(name="ctf_challenge_solver", description="Solve CTF challenges and security puzzles.")
async def ctf_challenge_solver(challenge: str) -> dict[str, Any]:
    start = time.monotonic()
    logger.info("ctf_challenge_solver start")
    
    try:
        answer = ctf_agent.run(challenge)
        logger.info("ctf_challenge_solver complete %.2fs", time.monotonic() - start)
        return {"agent": "redteam", "solution": answer}
    except Exception as e:
        logger.error("ctf_challenge_solver error: %s", e)
        return {"agent": "redteam", "error": str(e)}


def build_model() -> OpenAIModel:
    """Build the model using configuration."""
    api_key = config.model.api_key
    if not api_key:
        raise RuntimeError("Set DEEPSEEK_API_KEY (or OPENAI_API_KEY) before starting the red team A2A server.")

    logger.info("Red team agent using DeepSeek base_url=%s timeout=%.1fs", config.model.base_url, config.model.timeout)

    return DeepSeekOpenAIModel(
        client_args={
            "api_key": api_key,
            "base_url": config.model.base_url,
            "timeout": config.model.timeout,
        },
        model_id=config.model.model_id,
        params={
            "max_tokens": config.model.max_tokens,
            "temperature": config.model.temperature,
        },
    )


def build_agent() -> Agent:
    """Build the Strands agent using configuration."""
    return Agent(
        name=config.agent.name,
        description=config.agent.description,
        system_prompt=config.agent.system_prompt,
        model=build_model(),
        tools=[
            red_team_assess,
            exploit_discovery,
            ctf_challenge_solver,
        ],
    )


def build_server() -> A2AServer:
    """Build the A2A server using configuration."""
    host = os.getenv("REDTEAM_AGENT_HOST", "127.0.0.1")
    port = int(os.getenv("REDTEAM_AGENT_PORT", "9093"))
    public_url = os.getenv("REDTEAM_AGENT_PUBLIC_URL")

    return A2AServer(
        agent=build_agent(),
        host=host,
        port=port,
        http_url=public_url,
        version=os.getenv("REDTEAM_AGENT_VERSION", "0.1.0"),
    )


def main() -> None:
    server = build_server()
    server.serve(app_type="fastapi")


if __name__ == "__main__":
    main()

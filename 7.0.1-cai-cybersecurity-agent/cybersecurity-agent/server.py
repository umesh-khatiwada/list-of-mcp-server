"""Expose the CAI cybersecurity agent over the A2A protocol."""

from __future__ import annotations

import importlib.util
import logging
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

from config import get_config

logger = logging.getLogger("cai.cybersecurity.server")
logging.basicConfig(level=logging.INFO)

MODULE_PATH = Path(__file__).with_name("cybersecurity.py")
SPEC = importlib.util.spec_from_file_location("cai_cybersecurity", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise ImportError(f"Unable to load cybersecurity module from {MODULE_PATH}")

cybersecurity_module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cybersecurity_module)
CyberSecurityAgent = getattr(cybersecurity_module, "CyberSecurityAgent")

from strands import Agent, tool
from strands.models.openai import OpenAIModel
from strands.multiagent.a2a.server import A2AServer

# Load configuration
config = get_config()


class DeepSeekOpenAIModel(OpenAIModel):
    """OpenAIModel subclass that flattens text content for DeepSeek compatibility."""

    @staticmethod
    def _flatten_text_content(payload: dict[str, Any]) -> None:
        """Mutate the payload so text-only lists collapse into a single string."""

        for message in payload.get("messages", []):
            content = message.get("content")
            if (
                isinstance(content, list)
                and content
                and all(
                    isinstance(part, dict)
                    and part.get("type") == "text"
                    and "text" in part
                    for part in content
                )
            ):
                message["content"] = "\n\n".join(part["text"] for part in content)

    def format_request(self, *args, **kwargs):
        request = super().format_request(*args, **kwargs)
        self._flatten_text_content(request)
        return request


cybersecurity_agent = CyberSecurityAgent()


@tool(
    name="cybersecurity_consult",
    description="Run an open-ended CAI cybersecurity consultation.",
)
async def cybersecurity_consult(question: str) -> dict[str, Any]:
    start = time.monotonic()
    logger.info("cybersecurity_consult start")
    answer = await cybersecurity_agent.respond(question)
    logger.info("cybersecurity_consult complete %.2fs", time.monotonic() - start)
    return {"agent": "cybersecurity", "answer": answer}


@tool(
    name="security_posture_analysis",
    description="Assess security posture given reconnaissance and vulnerability findings.",
)
async def security_posture_analysis(analysis_context: dict[str, Any]) -> dict[str, Any]:
    start = time.monotonic()
    logger.info("security_posture_analysis start")
    result = await cybersecurity_agent.analyze_security_posture(analysis_context)
    logger.info("security_posture_analysis complete %.2fs", time.monotonic() - start)
    return result


@tool(
    name="threat_modeling",
    description="Run threat modeling for the supplied target context.",
)
async def threat_modeling(target: dict[str, Any]) -> dict[str, Any]:
    start = time.monotonic()
    logger.info("threat_modeling start")
    result = await cybersecurity_agent.perform_threat_modeling(target)
    logger.info("threat_modeling complete %.2fs", time.monotonic() - start)
    return result


@tool(
    name="compliance_assessment",
    description="Evaluate compliance against a named framework.",
)
async def compliance_assessment(
    target: dict[str, Any], framework: str = "OWASP"
) -> dict[str, Any]:
    start = time.monotonic()
    logger.info("compliance_assessment start")
    result = await cybersecurity_agent.assess_compliance(target, framework)
    logger.info("compliance_assessment complete %.2fs", time.monotonic() - start)
    return result


def build_cai_model() -> OpenAIModel:
    """Build the CAI model using configuration."""
    api_key = config.model.api_key
    if not api_key:
        raise RuntimeError(
            "Set DEEPSEEK_API_KEY (or OPENAI_API_KEY) before starting the cybersecurity A2A server."
        )

    logger.info(
        "Cybersecurity agent using DeepSeek base_url=%s timeout=%.1fs",
        config.model.base_url,
        config.model.timeout,
    )

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
        system_prompt=config.agent.system_prompt or cybersecurity_agent.instructions,
        model=build_cai_model(),
        tools=[
            cybersecurity_consult,
            security_posture_analysis,
            threat_modeling,
            compliance_assessment,
        ],
    )


def build_server() -> A2AServer:
    """Build the A2A server using configuration."""
    return A2AServer(
        agent=build_agent(),
        host=config.server.host,
        port=config.server.port,
        http_url=config.server.public_url,
        version=config.server.version,
    )


def main() -> None:
    server = build_server()
    server.serve(app_type="fastapi")


if __name__ == "__main__":
    main()

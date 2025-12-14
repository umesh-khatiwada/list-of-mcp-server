"""Expose the CAI cybersecurity agent over the A2A protocol."""

from __future__ import annotations

import importlib.util
import logging
import os
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

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


cybersecurity_agent = CyberSecurityAgent()


@tool(name="cybersecurity_consult", description="Run an open-ended CAI cybersecurity consultation.")
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


@tool(name="threat_modeling", description="Run threat modeling for the supplied target context.")
async def threat_modeling(target: dict[str, Any]) -> dict[str, Any]:
    start = time.monotonic()
    logger.info("threat_modeling start")
    result = await cybersecurity_agent.perform_threat_modeling(target)
    logger.info("threat_modeling complete %.2fs", time.monotonic() - start)
    return result


@tool(name="compliance_assessment", description="Evaluate compliance against a named framework.")
async def compliance_assessment(target: dict[str, Any], framework: str = "OWASP") -> dict[str, Any]:
    start = time.monotonic()
    logger.info("compliance_assessment start")
    result = await cybersecurity_agent.assess_compliance(target, framework)
    logger.info("compliance_assessment complete %.2fs", time.monotonic() - start)
    return result


def build_cai_model() -> OpenAIModel:
    api_key = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set DEEPSEEK_API_KEY (or OPENAI_API_KEY) before starting the cybersecurity A2A server.")

    base_url = os.getenv("DEEPSEEK_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "https://api.deepseek.ai/v1/"
    timeout = float(os.getenv("CYBERSECURITY_AGENT_TIMEOUT", "60"))

    logger.info("Cybersecurity agent using DeepSeek base_url=%s timeout=%.1fs", base_url, timeout)

    return DeepSeekOpenAIModel(
        client_args={
            "api_key": api_key,
            "base_url": base_url,
            "timeout": timeout,
        },
        model_id=os.getenv("CAI_MODEL", "deepseek-chat"),
        params={
            "max_tokens": 600,
            "temperature": float(os.getenv("CYBERSECURITY_AGENT_TEMPERATURE", "0.2")),
        },
    )


def build_agent() -> Agent:
    return Agent(
        name="cai-cybersecurity-agent",
        description="CAI cybersecurity specialist available via A2A",
        system_prompt=cybersecurity_agent.instructions,
        model=build_cai_model(),
        tools=[
            cybersecurity_consult,
            security_posture_analysis,
            threat_modeling,
            compliance_assessment,
        ],
    )


def build_server() -> A2AServer:
    host = os.getenv("CYBERSECURITY_AGENT_HOST", "127.0.0.1")
    port = int(os.getenv("CYBERSECURITY_AGENT_PORT", "9003"))
    public_url = os.getenv("CYBERSECURITY_AGENT_PUBLIC_URL")

    return A2AServer(
        agent=build_agent(),
        host=host,
        port=port,
        http_url=public_url,
        version=os.getenv("CYBERSECURITY_AGENT_VERSION", "0.1.0"),
    )


def main() -> None:
    server = build_server()
    server.serve(app_type="fastapi")


if __name__ == "__main__":
    main()

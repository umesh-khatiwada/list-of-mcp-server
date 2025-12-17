"""Configuration for Red Team Agent."""

import os
from dataclasses import dataclass


@dataclass
class ModelConfig:
    """Model configuration for red team agent."""
    model_id: str = os.getenv("CAI_MODEL", "deepseek-chat")
    api_key: str = os.getenv("DEEPSEEK_API_KEY", "") or os.getenv("OPENAI_API_KEY", "")
    base_url: str = os.getenv("DEEPSEEK_BASE_URL") or os.getenv("OPENAI_BASE_URL", "https://api.deepseek.ai/v1/")
    timeout: float = float(os.getenv("REDTEAM_AGENT_TIMEOUT", "60"))
    max_tokens: int = int(os.getenv("REDTEAM_AGENT_MAX_TOKENS", "1000"))
    temperature: float = float(os.getenv("REDTEAM_AGENT_TEMPERATURE", "0.7"))


@dataclass
class AgentConfig:
    """Agent configuration."""
    name: str = os.getenv("AGENT_NAME", "redteam-agent")
    description: str = os.getenv("AGENT_DESCRIPTION", "Red team security agent for CTF and penetration testing")
    system_prompt: str = os.getenv("AGENT_SYSTEM_PROMPT", "You are a cybersecurity expert leader conducting red team operations and security challenges (CTF)")


@dataclass
class RedTeamConfig:
    """Main red team configuration."""
    model: ModelConfig
    agent: AgentConfig

    @classmethod
    def from_env(cls) -> "RedTeamConfig":
        """Create configuration from environment variables."""
        return cls(
            model=ModelConfig(),
            agent=AgentConfig()
        )


# Load configuration once at module import
_config = None


def get_config() -> RedTeamConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = RedTeamConfig.from_env()
    return _config

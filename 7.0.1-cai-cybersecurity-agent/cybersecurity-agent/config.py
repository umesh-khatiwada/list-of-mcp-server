"""Configuration management for the Cybersecurity Agent."""

import os
from dataclasses import dataclass


@dataclass
class ModelConfig:
    """Model configuration."""

    model_id: str = os.getenv("CAI_MODEL", "deepseek-chat")
    api_key: str = os.getenv("DEEPSEEK_API_KEY") or os.getenv("OPENAI_API_KEY", "")
    base_url: str = os.getenv("DEEPSEEK_BASE_URL") or os.getenv(
        "OPENAI_BASE_URL", "https://api.deepseek.ai/v1/"
    )
    timeout: float = float(os.getenv("MODEL_TIMEOUT", "60"))
    max_tokens: int = int(os.getenv("MODEL_MAX_TOKENS", "600"))
    temperature: float = float(os.getenv("MODEL_TEMPERATURE", "0.2"))

    def validate(self) -> None:
        """Validate configuration."""
        if not self.api_key:
            raise RuntimeError(
                "Set DEEPSEEK_API_KEY (or OPENAI_API_KEY) environment variable."
            )


@dataclass
class ServerConfig:
    """Server configuration."""

    host: str = os.getenv("CYBERSECURITY_AGENT_HOST", "127.0.0.1")
    port: int = int(os.getenv("CYBERSECURITY_AGENT_PORT", "9003"))
    public_url: str = os.getenv("CYBERSECURITY_AGENT_PUBLIC_URL", "")
    version: str = os.getenv("CYBERSECURITY_AGENT_VERSION", "0.1.0")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"


@dataclass
class AgentConfig:
    """Agent configuration."""

    name: str = os.getenv("AGENT_NAME", "cai-cybersecurity-agent")
    description: str = os.getenv(
        "AGENT_DESCRIPTION", "CAI cybersecurity specialist available via A2A"
    )
    system_prompt: str = os.getenv(
        "AGENT_SYSTEM_PROMPT",
        "You are a cybersecurity specialist. Provide brief, actionable security guidance. "
        "Focus on critical findings only. Be concise.",
    )


@dataclass
class Config:
    """Main configuration container."""

    model: ModelConfig
    server: ServerConfig
    agent: AgentConfig

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        config = cls(model=ModelConfig(), server=ServerConfig(), agent=AgentConfig())
        config.model.validate()
        return config


# Load configuration once at module import
_config = None


def get_config() -> Config:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = Config.from_env()
    return _config

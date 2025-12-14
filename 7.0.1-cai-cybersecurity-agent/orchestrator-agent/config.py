"""Configuration management for the Orchestrator Agent."""

import os
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ModelConfig:
    """Model configuration for orchestrator."""
    model_id: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    base_url: str = os.getenv("DEEPSEEK_BASE_URL") or os.getenv("OPENAI_BASE_URL", "https://api.deepseek.ai/v1/")
    timeout: float = float(os.getenv("ORCHESTRATOR_DEEPSEEK_TIMEOUT", "60"))
    max_tokens: int = int(os.getenv("ORCHESTRATOR_MAX_TOKENS", "2000"))
    temperature: float = float(os.getenv("ORCHESTRATOR_TEMPERATURE", "0.7"))


@dataclass
class AgentConfig:
    """Agent discovery and configuration."""
    urls: List[str] = None
    cybersecurity_agent_url: Optional[str] = None
    session_id: str = os.getenv("SESSION_ID", "default-session")
    enable_memory: bool = os.getenv("ORCHESTRATOR_ENABLE_MEMORY", "false").lower() == "true"

    def __post_init__(self):
        """Parse and merge agent URLs."""
        if self.urls is None:
            raw_urls = os.getenv("ORCHESTRATOR_AGENT_URLS", "")
            self.urls = [u.strip() for u in raw_urls.split(",") if u.strip()] if raw_urls else []
        
        # Add cybersecurity agent if specified
        if self.cybersecurity_agent_url is None:
            self.cybersecurity_agent_url = os.getenv("CYBERSECURITY_AGENT_URL")
        
        if self.cybersecurity_agent_url:
            self.urls.append(self.cybersecurity_agent_url.strip())
        
        # Remove duplicates while preserving order
        self.urls = list(dict.fromkeys(self.urls))


@dataclass
class OrchestratorConfig:
    """Main orchestrator configuration."""
    model: ModelConfig
    agent: AgentConfig

    @classmethod
    def from_env(cls) -> "OrchestratorConfig":
        """Create configuration from environment variables."""
        return cls(
            model=ModelConfig(),
            agent=AgentConfig()
        )


# Load configuration once at module import
_config = None


def get_config() -> OrchestratorConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = OrchestratorConfig.from_env()
    return _config

"""Application configuration module."""
import os
from dataclasses import dataclass


@dataclass
class Settings:
    """Application settings."""

    # Kubernetes Configuration
    namespace: str = os.getenv("NAMESPACE", "default")
    cai_image: str = os.getenv("CAI_IMAGE", "docker.io/neptune1212/kali-cai:arm64")

    # API Keys
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    alias_api_key: str = os.getenv("ALIAS_API_KEY", "")

    # CAI Configuration
    cai_model: str = os.getenv(
        "CAI_MODEL", "deepseek/deepseek-chat"
    )  # Default to alias1 for cybersecurity
    cai_stream: str = os.getenv("CAI_STEAM", "false")  # Disable streaming for K8s
    cai_agent_type: str = os.getenv("CAI_AGENT_TYPE", "redteam_agent")

    # Webhook Configuration
    webhook_url: str = os.getenv("WEBHOOK_URL", "")

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000

    # Worker Configuration
    webhook_max_workers: int = 5


# Global settings instance
settings = Settings()

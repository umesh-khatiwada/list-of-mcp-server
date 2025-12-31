"""Application configuration module."""
import logging
import os
import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class Settings:
    """Application settings."""

    # Kubernetes Configuration
    namespace: str = os.getenv("NAMESPACE", "default")
    managed_cluster_namespace: str = os.getenv("MANAGED_CLUSTER_NAMESPACE", "east")
    cai_image: str = os.getenv("CAI_IMAGE", "neptune1212/kali-cai:amd64")

    # API Keys
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    # OpenAI API key is optional; only needed if using OpenAI models
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")

    # CAI Configuration
    cai_model: str = os.getenv(
        "CAI_MODEL", "deepseek/deepseek-chat"
    )  # Default to alias1 for cybersecurity
    cai_stream: str = os.getenv("CAI_STEAM", "true")  # Disable streaming for K8s
    cai_agent_type: str = os.getenv("CAI_AGENT_TYPE", "redteam_agent")

    # Webhook Configuration
    webhook_url: str = os.getenv("WEBHOOK_URL", "")
    # Loki (logs) Configuration
    loki_url: str = os.getenv("LOKI_URL", "")

    # Server Configuration
    host: str = "0.0.0.0"
    port: int = 8000

    # Worker Configuration
    webhook_max_workers: int = 5

    # Security Configuration
    enable_audit_logging: bool = (
        os.getenv("ENABLE_AUDIT_LOGGING", "true").lower() == "true"
    )
    max_prompt_length: int = int(os.getenv("MAX_PROMPT_LENGTH", "10000"))
    allowed_commands: List[str] = field(
        default_factory=lambda: os.getenv(
            "ALLOWED_COMMANDS", "cai,ping,curl,nmap"
        ).split(",")
    )

    def __post_init__(self):
        """Validate configuration on initialization."""
        self._validate_configuration()
        self._setup_logging()

    def _validate_configuration(self):
        """Validate security configuration."""
        # Validate DeepSeek API key for production
        if not self._is_development_mode():
            if not self.deepseek_api_key or self.deepseek_api_key.startswith("sk-placeholder"):
                logging.warning("DeepSeek API key not properly configured for production")
        # Validate webhook URL if provided
        if self.webhook_url and not self._is_valid_url(self.webhook_url):
            raise ValueError(f"Invalid webhook URL: {self.webhook_url}")

    def _is_development_mode(self) -> bool:
        """Check if running in development mode."""
        return os.getenv("ENVIRONMENT", "production").lower() in [
            "dev",
            "development",
            "local",
        ]

    def _is_valid_url(self, url: str) -> bool:
        """Validate URL format."""
        url_pattern = re.compile(
            r"^https?://"  # http:// or https://
            r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+"  # domain
            r"(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|"  # host
            r"localhost|"  # localhost
            r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # IP
            r"(?::\d+)?"  # optional port
            r"(?:/?|[/?]\S+)$",
            re.IGNORECASE,
        )
        return bool(url_pattern.match(url))

    def _setup_logging(self):
        """Setup secure logging configuration."""
        if self.enable_audit_logging:
            logging.basicConfig(
                level=logging.INFO,
                format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            )

    def get_masked_config(self) -> dict:
        """Get configuration with sensitive data masked for logging."""
        return {
            "namespace": self.namespace,
            "cai_image": self.cai_image,
            "deepseek_api_key": "***" if self.deepseek_api_key else "not_set",
            # Only show OpenAI key if model is set to OpenAI
            "openai_api_key": "***" if (self.openai_api_key and self.cai_model.startswith("openai")) else "not_needed",
            "cai_model": self.cai_model,
            "cai_stream": self.cai_stream,
            "cai_agent_type": self.cai_agent_type,
            "loki_url": self.loki_url if self.loki_url else "not_set",
            "webhook_url": "***" if self.webhook_url else "not_set",
            "host": self.host,
            "port": self.port,
            "enable_audit_logging": self.enable_audit_logging,
        }


# Global settings instance
settings = Settings()

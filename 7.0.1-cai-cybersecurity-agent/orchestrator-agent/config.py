"""Configuration management for the Orchestrator Agent."""

import os
import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from pathlib import Path


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
class AgentRegistry:
    """Dynamic agent registry - agents register themselves via endpoint."""
    registry_file: str = os.getenv("AGENT_REGISTRY_FILE", "agent_registry.json")
    _agents: Dict[str, str] = field(default_factory=dict)  # name -> url mapping
    
    def __post_init__(self):
        """Load registry from file if it exists."""
        self._load_registry()
    
    def _load_registry(self):
        """Load registered agents from file."""
        registry_path = Path(self.registry_file)
        if registry_path.exists():
            try:
                with open(registry_path, 'r') as f:
                    data = json.load(f)
                    self._agents = data.get("agents", {})
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load agent registry: {e}")
                self._agents = {}
        else:
            self._agents = {}
    
    def _save_registry(self):
        """Save registered agents to file."""
        registry_path = Path(self.registry_file)
        with open(registry_path, 'w') as f:
            json.dump({"agents": self._agents}, f, indent=2)
    
    def register(self, name: str, url: str) -> bool:
        """Register an agent dynamically."""
        self._agents[name] = url
        self._save_registry()
        return True
    
    def unregister(self, name: str) -> bool:
        """Unregister an agent."""
        if name in self._agents:
            del self._agents[name]
            self._save_registry()
            return True
        return False
    
    def get_urls(self) -> List[str]:
        """Get all registered agent URLs."""
        return list(self._agents.values())
    
    def get_agents(self) -> Dict[str, str]:
        """Get all registered agents as dict."""
        return self._agents.copy()
    
    def get_url(self, name: str) -> Optional[str]:
        """Get URL for a specific agent."""
        return self._agents.get(name)


@dataclass
class AgentConfig:
    """Agent discovery and configuration."""
    urls: List[str] = field(default_factory=list)
    session_id: str = os.getenv("SESSION_ID", "default-session")
    enable_memory: bool = os.getenv("ORCHESTRATOR_ENABLE_MEMORY", "false").lower() == "true"
    registry: AgentRegistry = field(default_factory=AgentRegistry)

    def __post_init__(self):
        """Initialize with dynamically registered agents."""
        # Use only dynamically registered agents
        self.urls = self.registry.get_urls()
        
        # Optionally load from legacy env vars if no agents registered yet
        if not self.urls:
            raw_urls = os.getenv("ORCHESTRATOR_AGENT_URLS", "")
            legacy_urls = [u.strip() for u in raw_urls.split(",") if u.strip()] if raw_urls else []
            
            # Load legacy CYBERSECURITY_AGENT_URL if set
            legacy_cyber = os.getenv("CYBERSECURITY_AGENT_URL")
            if legacy_cyber:
                legacy_urls.append(legacy_cyber.strip())
            
            # Remove duplicates while preserving order
            self.urls = list(dict.fromkeys(legacy_urls))


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

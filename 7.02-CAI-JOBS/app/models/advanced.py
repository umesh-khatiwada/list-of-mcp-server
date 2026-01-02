"""Advanced job creation models for parallel execution and complex workflows."""
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .mcp import MCPServerConfig


class AgentType(str, Enum):
    """Available CAI agent types."""

    REDTEAM = "redteam_agent"
    BLUETEAM = "blueteam_agent"
    BUG_BOUNTY = "bug_bounter_agent"
    DFIR = "dfir_agent"
    NETWORK_SECURITY = "network_security_analyzer_agent"
    REVERSE_ENGINEERING = "reverse_engineering_agent"
    REPORTING = "reporting_agent"
    SELECTION = "selection_agent"


class ModelType(str, Enum):
    """Available models."""

    ALIAS1 = "alias1"
    GPT_4O = "gpt-4o"
    CLAUDE_SONNET = "claude-3-5-sonnet-20241022"
    DEEPSEEK_CHAT = "deepseek/deepseek-chat"


class MemoryType(str, Enum):
    """Memory management types."""

    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    ALL = "all"
    NONE = "none"


class ParallelAgentConfig(BaseModel):
    """Configuration for a parallel agent."""

    name: str
    agent_type: AgentType
    model: ModelType
    initial_prompt: Optional[str] = None
    alias: Optional[str] = None


class AgentMCPMapping(BaseModel):
    """Bind MCP servers to a specific agent type."""

    agent_type: AgentType
    mcp_servers: List[MCPServerConfig]


class QueueItem(BaseModel):
    """Queue item for batch processing."""

    command: str
    description: Optional[str] = None
    agent_type: Optional[AgentType] = None
    expected_duration_minutes: Optional[int] = None


class CTFConfig(BaseModel):
    """CTF-specific configuration."""

    ctf_name: str
    challenge_name: Optional[str] = None
    challenge_type: Optional[str] = None  # web, pwn, forensics, crypto
    subnet: Optional[str] = None
    target_ip: Optional[str] = None
    inside_container: bool = True
    time_limit_minutes: Optional[int] = None


class VolcanoConfig(BaseModel):
    """Volcano-specific configuration."""

    enabled: bool = False
    queue: str = "default"
    min_available: int = 1
    replicas: int = 1
    scheduler_name: str = "volcano"
    priority_class: Optional[str] = None


class CostConstraints(BaseModel):
    """Cost management configuration."""

    price_limit: float = 10.0
    max_interactions: Optional[int] = 100
    max_turns: Optional[int] = 50
    auto_compact: bool = False


class AdvancedSessionCreate(BaseModel):
    """Advanced session creation with multiple execution modes."""

    name: str

    # Basic execution
    prompt: Optional[str] = None

    # Agent configuration
    agent_type: AgentType = AgentType.REDTEAM
    model: ModelType = ModelType.ALIAS1

    # MCP integrations
    mcp_servers: Optional[List[MCPServerConfig]] = None
    mcp_agent_overrides: Optional[List[AgentMCPMapping]] = None

    # Parallel execution
    parallel_agents: Optional[List[ParallelAgentConfig]] = None

    # Queue execution
    queue_items: Optional[List[QueueItem]] = None
    queue_file_content: Optional[str] = None

    # CTF mode
    ctf_config: Optional[CTFConfig] = None

    # Volcano configuration
    volcano_config: Optional[VolcanoConfig] = None

    # Memory management
    memory_type: MemoryType = MemoryType.NONE
    load_memory_ids: Optional[List[str]] = None

    # Cost constraints
    cost_constraints: CostConstraints = Field(default_factory=CostConstraints)

    # Workspace & Virtualization
    workspace_path: Optional[str] = None
    docker_container: Optional[str] = None

    # Advanced options
    debug_level: int = 0
    tracing_enabled: bool = False
    auto_save_interval: Optional[int] = None
    webhook_notifications: bool = True

    # Authentication
    character_id: Optional[str] = None
    token: Optional[str] = None


class SessionMode(str, Enum):
    """Session execution modes."""

    SINGLE = "single"
    PARALLEL = "parallel"
    QUEUE = "queue"
    CTF = "ctf"
    AUTOMATION = "automation"


class SessionStatus(BaseModel):
    """Enhanced session status."""

    id: str
    name: str
    mode: SessionMode
    status: str
    created: str

    # Job information
    job_names: List[str]  # Multiple jobs for parallel execution

    # Progress tracking
    current_step: Optional[str] = None
    total_steps: Optional[int] = None
    completed_steps: int = 0

    # Cost tracking
    estimated_cost: Optional[float] = None
    actual_cost: Optional[float] = None
    cost_limit: float = 10.0

    # Results
    outputs: Dict[str, Any] = Field(default_factory=dict)
    flags_found: List[str] = Field(default_factory=list)
    vulnerabilities: List[str] = Field(default_factory=list)

    # Original config for reference
    original_config: Dict[str, Any] = Field(default_factory=dict)

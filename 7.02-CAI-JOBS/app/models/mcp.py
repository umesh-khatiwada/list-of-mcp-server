"""Models for describing and validating MCP server connections."""
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, model_validator


class MCPTransport(str, Enum):
    """Supported MCP transport types."""

    SSE = "sse"
    STDIO = "stdio"


class MCPServerConfig(BaseModel):
    """Configuration for an MCP server to be preloaded by CAI."""

    name: str = Field(..., min_length=1, description="Alias used when loading the MCP server")
    transport: MCPTransport = Field(..., description="Transport type: sse or stdio")
    url: Optional[str] = Field(None, description="SSE endpoint URL, e.g. http://host:port/sse")
    command: Optional[str] = Field(None, description="Command to launch for stdio transport")
    allow_insecure: bool = Field(
        False,
        description="Allow insecure HTTP when probing SSE endpoints",
    )

    @model_validator(mode="after")
    def validate_target(self) -> "MCPServerConfig":
        """Ensure the required target is present for each transport."""
        if self.transport == MCPTransport.SSE and not self.url:
            raise ValueError("url is required for sse transport")
        if self.transport == MCPTransport.STDIO and not self.command:
            raise ValueError("command is required for stdio transport")
        return self

    def target_display(self) -> str:
        """Return a human-readable target string."""
        return self.url or self.command or self.name


class MCPTestRequest(BaseModel):
    """Payload for testing MCP connectivity."""

    servers: List[MCPServerConfig] = Field(
        ..., min_items=1, description="List of MCP servers to test"
    )
    timeout: float = Field(
        5.0, ge=1.0, le=60.0, description="Timeout (seconds) for SSE endpoint probes"
    )


class MCPTestResult(BaseModel):
    """Result of an MCP connectivity test."""

    name: str
    transport: MCPTransport
    target: str
    reachable: bool
    status: Optional[str] = None
    detail: Optional[str] = None
    status_code: Optional[int] = None
    latency_ms: Optional[int] = None

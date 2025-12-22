"""Pydantic models for the application."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from .mcp import MCPServerConfig


class SessionCreate(BaseModel):
    """Model for creating a new session."""

    name: str
    prompt: str
    character_id: Optional[str] = None
    token: Optional[str] = None
    mcp_servers: Optional[List[MCPServerConfig]] = None
    workspace_path: Optional[str] = None


class Session(BaseModel):
    """Model for a chat session."""

    id: str
    name: str
    status: str
    created: str
    jobName: str
    prompt: str
    workspace_path: Optional[str] = None


class JobLogs(BaseModel):
    """Model for job logs."""

    logs: str
    status: str


class JobResult(BaseModel):
    """Model for job results."""

    session_id: str
    status: str
    log_path: Optional[str] = None
    pod_logs: Optional[str] = None
    file_content: Optional[str] = None
    file_size: Optional[int] = None


class WebhookPayload(BaseModel):
    """Model for webhook payload."""

    session_id: str
    job_name: str
    status: str
    timestamp: str
    log_path: Optional[str] = None
    pod_logs: Optional[str] = None
    file_content: Optional[str] = None


__all__ = [
    "SessionCreate",
    "Session",
    "JobLogs",
    "JobResult",
    "WebhookPayload",
    "MCPServerConfig",
]

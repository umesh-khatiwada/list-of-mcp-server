"""Routes for testing MCP connectivity and configuration."""
import logging
import os
import time
from typing import List

import requests
from fastapi import APIRouter

from ...config import settings
from ...models.mcp import MCPTestRequest, MCPTestResult, MCPTransport

router = APIRouter(prefix="/api/mcp", tags=["mcp"])
logger = logging.getLogger(__name__)


@router.get("/agents", response_model=List[str])
def list_mcp_agents() -> List[str]:
    """Return agent names configured via environment.

    Prefers a comma-separated CAI_AGENTS env var; falls back to CAI_AGENT_TYPE
    (single value) from settings/env. Empty or missing values yield an empty list.
    """

    env_value = os.getenv("CAI_AGENTS") or settings.cai_agent_type
    if not env_value:
        return []

    agents = [item.strip() for item in env_value.split(",") if item.strip()]
    return agents


@router.post("/test", response_model=List[MCPTestResult])
def test_mcp_connections(payload: MCPTestRequest) -> List[MCPTestResult]:
    """Probe configured MCP endpoints to verify connectivity.

    SSE endpoints are fetched over HTTP(S) and marked reachable on < 400 status.
    Stdio transports cannot be probed over HTTP, so we echo back the provided
    command and mark the target as recorded.
    """

    results: List[MCPTestResult] = []

    for server in payload.servers:
        target = server.target_display()

        if server.transport == MCPTransport.STDIO:
            reachable = bool(server.command)
            detail = "Stdio transports are not probed over HTTP; command captured for CAI"
            results.append(
                MCPTestResult(
                    name=server.name,
                    transport=server.transport,
                    target=target,
                    reachable=reachable,
                    status="not-probed",
                    detail=detail,
                    status_code=None,
                    latency_ms=None,
                )
            )
        elif server.transport == MCPTransport.SSE:
            try:
                start = time.perf_counter()
                # Use stream=True so we return after headers without downloading the endless SSE body.
                with requests.get(
                    server.url,
                    headers={"Accept": "text/event-stream"},
                    timeout=payload.timeout,
                    verify=not server.allow_insecure,
                    stream=True,
                ) as response:
                    latency_ms = int((time.perf_counter() - start) * 1000)
                    reachable = response.status_code < 400
                    results.append(
                        MCPTestResult(
                            name=server.name,
                            transport=server.transport,
                            target=target,
                            reachable=reachable,
                            status=f"HTTP {response.status_code}",
                            detail=response.headers.get("content-type"),
                            status_code=response.status_code,
                            latency_ms=latency_ms,
                        )
                    )
            except Exception as exc:  # pragma: no cover - network exceptions
                logger.warning("MCP SSE probe failed for %s: %s", target, exc)
                results.append(
                    MCPTestResult(
                        name=server.name,
                        transport=server.transport,
                        target=target,
                        reachable=False,
                        status="connection-error",
                        detail=str(exc),
                        status_code=None,
                        latency_ms=None,
                    )
                )

    return results

"""
Agent Registry Service - HTTP endpoint for dynamic agent registration.

Provides REST API endpoints to register, unregister, and list agents dynamically.
"""

import logging
from typing import Dict

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class AgentRegistrationRequest(BaseModel):
    """Request model for agent registration."""

    name: str
    url: str


class AgentResponse(BaseModel):
    """Response model for agent information."""

    name: str
    url: str


class RegistryResponse(BaseModel):
    """Response model for registry listing."""

    agents: Dict[str, str]
    count: int


def create_registry_app(config) -> FastAPI:
    """Create FastAPI app for agent registry endpoints."""
    app = FastAPI(
        title="Agent Registry API",
        description="Dynamic agent registration and discovery",
        version="1.0.0",
    )

    @app.post("/register", response_model=AgentResponse, tags=["Registry"])
    async def register_agent(request: AgentRegistrationRequest):
        """
        Register a new agent dynamically.

        Args:
            request: AgentRegistrationRequest with name and url

        Returns:
            AgentResponse with registered agent details

        Example:
            POST /register
            {"name": "cybersecurity-agent", "url": "http://127.0.0.1:9003"}
        """
        try:
            config.agent.registry.register(request.name, request.url)

            # Update orchestrator's agent list
            config.agent.urls = config.agent.registry.get_urls()

            logger.info(f"Agent registered: {request.name} -> {request.url}")
            return AgentResponse(name=request.name, url=request.url)
        except Exception as e:
            logger.error(f"Failed to register agent: {e}")
            raise HTTPException(status_code=400, detail=str(e))

    @app.delete("/unregister/{agent_name}", tags=["Registry"])
    async def unregister_agent(agent_name: str):
        """
        Unregister an agent.

        Args:
            agent_name: Name of agent to unregister

        Returns:
            Message confirming unregistration

        Example:
            DELETE /unregister/cybersecurity-agent
        """
        if config.agent.registry.unregister(agent_name):
            # Update orchestrator's agent list
            config.agent.urls = config.agent.registry.get_urls()

            logger.info(f"Agent unregistered: {agent_name}")
            return {"message": f"Agent '{agent_name}' unregistered"}
        else:
            raise HTTPException(
                status_code=404, detail=f"Agent '{agent_name}' not found"
            )

    @app.get("/agents", response_model=RegistryResponse, tags=["Registry"])
    async def list_agents():
        """
        List all registered agents.

        Returns:
            RegistryResponse with all registered agents and count

        Example:
            GET /agents
        """
        agents = config.agent.registry.get_agents()
        return RegistryResponse(agents=agents, count=len(agents))

    @app.get("/agents/{agent_name}", response_model=AgentResponse, tags=["Registry"])
    async def get_agent(agent_name: str):
        """
        Get details of a specific agent.

        Args:
            agent_name: Name of agent to retrieve

        Returns:
            AgentResponse with agent details

        Example:
            GET /agents/cybersecurity-agent
        """
        url = config.agent.registry.get_url(agent_name)
        if url:
            return AgentResponse(name=agent_name, url=url)
        else:
            raise HTTPException(
                status_code=404, detail=f"Agent '{agent_name}' not found"
            )

    @app.get("/health", tags=["Health"])
    async def health():
        """Health check endpoint."""
        return {
            "status": "healthy",
            "registered_agents": len(config.agent.registry.get_agents()),
        }

    return app


# Example usage and documentation
if __name__ == "__main__":
    print(
        """
    Agent Registry Service
    =====================

    Register agents dynamically via HTTP endpoints:

    1. Register an agent:
       POST http://localhost:8000/register
       {"name": "cybersecurity-agent", "url": "http://127.0.0.1:9003"}

    2. List all registered agents:
       GET http://localhost:8000/agents

    3. Get specific agent:
       GET http://localhost:8000/agents/cybersecurity-agent

    4. Unregister an agent:
       DELETE http://localhost:8000/unregister/cybersecurity-agent

    5. Health check:
       GET http://localhost:8000/health
    """
    )

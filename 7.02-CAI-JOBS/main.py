"""CAI Kubernetes Job Manager - Main Application Entry Point."""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import health, mcp, sessions, webhooks

try:
    from app.api.routes import advanced_sessions

    advanced_available = True
except ImportError:
    advanced_available = False
from app.api.dependencies import get_kubernetes_service
from app.config import settings
from app.services.job_monitor import monitor_jobs
from app.services.session_store import sessions_store

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("CAI Kubernetes Job Manager started")

    # Sync existing jobs on startup
    try:
        k8s_service = get_kubernetes_service()
        jobs = k8s_service.list_jobs()

        for job in jobs:
            if "session-id" in job.metadata.labels:
                session_id = job.metadata.labels["session-id"]
                if session_id not in sessions_store:
                    sessions_store[session_id] = {
                        "id": session_id,
                        "name": job.metadata.labels.get("session-name", "Unknown"),
                        "status": k8s_service.get_job_status(job.metadata.name),
                        "created": job.metadata.creation_timestamp.isoformat(),
                        "jobName": job.metadata.name,
                        "prompt": "Recovered from existing job",
                    }
        logger.info(f"Synced {len(sessions_store)} existing sessions")
    except Exception as e:
        logger.error(f"Failed to sync existing jobs: {str(e)}")

    # Start background job monitor
    monitor_task = asyncio.create_task(monitor_jobs())
    logger.info("Background job monitor started")

    yield

    # Shutdown
    logger.info("CAI Kubernetes Job Manager shutting down")
    monitor_task.cancel()
    try:
        await monitor_task
    except asyncio.CancelledError:
        logger.info("Background job monitor stopped")


# Create FastAPI app
app = FastAPI(title="CAI Kubernetes Job Manager", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sessions.router)
if advanced_available:
    app.include_router(advanced_sessions.router)
app.include_router(mcp.router)
app.include_router(health.router)
app.include_router(webhooks.router)

# Serve static files for UI
app.mount("/", StaticFiles(directory="ui", html=True), name="ui")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)

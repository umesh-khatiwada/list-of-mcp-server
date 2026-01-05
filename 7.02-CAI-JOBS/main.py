"""CAI Kubernetes Job Manager - Main Application Entry Point."""
import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import health, mcp, sessions, webhooks, monitoring

try:
    from app.api.routes import advanced_sessions

    advanced_available = True
except ImportError:
    advanced_available = False
from app.api.dependencies import get_kubernetes_service
from app.config import settings
from app.services.job_monitor import monitor_jobs
from app.services.session_store import sessions_store, load_sessions, save_sessions

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    logger.info("CAI Kubernetes Job Manager started")

    # Load sessions from file
    load_sessions()
    logger.info(f"Loaded {len(sessions_store)} sessions from file")

    # Sync existing jobs on startup (Legacy Sessions)
    try:
        k8s_service = get_kubernetes_service()
        jobs = k8s_service.list_jobs()

        for job in jobs:
            session_id = job.metadata.labels.get("session-id") if job.metadata.labels else None
            if session_id and session_id not in sessions_store:
                sessions_store[session_id] = {
                    "id": session_id,
                    "name": job.metadata.labels.get("session-name", "Unknown"),
                    "status": k8s_service.get_job_status(job.metadata.name),
                    "created": job.metadata.creation_timestamp.isoformat() if job.metadata.creation_timestamp else datetime.now().isoformat(),
                    "jobName": job.metadata.name,
                    "prompt": "Recovered from existing job",
                }
    except Exception as e:
        logger.error(f"Failed to sync legacy jobs: {str(e)}")

    # Sync existing ManifestWorks (Advanced Sessions)
    try:
        from app.services.advanced_kubernetes_service import AdvancedKubernetesService
        adv_k8s = AdvancedKubernetesService()
        manifestworks = adv_k8s.list_manifestworks()

        for mw in manifestworks:
            mw_labels = mw.get('metadata', {}).get('labels', {})
            session_id = mw_labels.get("session-id")
            if session_id and session_id not in sessions_store:
                sessions_store[session_id] = {
                    "id": session_id,
                    "name": mw_labels.get("session-name", "Recovered Advanced Session"),
                    "status": adv_k8s.get_manifestwork_status(mw['metadata']['name']),
                    "created": mw['metadata'].get('creationTimestamp', datetime.now().isoformat()),
                    "job_names": [mw['metadata']['name']],
                    "mode": "recovered",
                    "prompt": "Recovered from existing ManifestWork",
                }
    except Exception as e:
        logger.error(f"Failed to sync manifestworks: {str(e)}")

    logger.info(f"Synced {len(sessions_store)} total sessions from cluster")
    save_sessions()

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
    
    # Save sessions before shutdown
    logger.info("Saving sessions before shutdown...")
    save_sessions()
    logger.info(f"Saved {len(sessions_store)} sessions to disk")


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
app.include_router(monitoring.router)

# Serve static files for UI
app.mount("/", StaticFiles(directory="ui", html=True), name="ui")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.host, port=settings.port)

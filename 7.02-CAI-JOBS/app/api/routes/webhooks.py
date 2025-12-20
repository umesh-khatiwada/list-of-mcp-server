"""Webhook routes."""
import logging

from fastapi import APIRouter, HTTPException

from ...services.session_store import sessions_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["webhooks"])


@router.post("/webhooks")
async def receive_webhook(payload: dict):
    """Receive webhook notifications from completed jobs."""
    try:
        session_id = payload.get("session_id")
        status = payload.get("status")
        log_path = payload.get("log_path")
        file_content = payload.get("file_content")
        pod_logs = payload.get("pod_logs")

        logger.info(f"Webhook received for session {session_id} with status {status}")
        logger.info(f"Log path: {log_path}")

        if file_content:
            logger.info(f"File content length: {len(file_content)} bytes")

        # Store the results in session store for later retrieval
        if session_id in sessions_store:
            sessions_store[session_id]["result"] = {
                "log_path": log_path,
                "file_content": file_content,
                "pod_logs": pod_logs,
                "status": status,
            }

        return {"status": "received", "session_id": session_id, "processed": True}
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

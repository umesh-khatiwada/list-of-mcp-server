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


@router.get("/webhooks/result/{session_id}")
async def get_webhook_result(session_id: str):
    """Show parsed result from saved webhook data for a session."""
    from fastapi.responses import JSONResponse
    from ...services.session_store import sessions_store
    import json

    result = sessions_store.get(session_id, {}).get("result")
    if not result:
        return JSONResponse(status_code=404, content={"error": "No result found for this session."})

    # Try to parse file_content as JSON if present
    file_content = result.get("file_content")
    parsed_json = None
    if file_content:
        try:
            parsed_json = json.loads(file_content)
        except Exception:
            parsed_json = file_content  # Return raw if not valid JSON

    return {
        "session_id": session_id,
        "status": result.get("status"),
        "log_path": result.get("log_path"),
        "pod_logs": result.get("pod_logs"),
        "parsed_file_content": parsed_json,
    }

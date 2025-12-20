"""Session management routes."""
import json
import logging
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from fastapi.responses import PlainTextResponse

from ...api.dependencies import get_kubernetes_service
from ...models import JobLogs, JobResult, Session, SessionCreate
from ...services import send_webhook
from ...services.kubernetes_service import KubernetesService
from ...services.session_store import sessions_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


@router.post("", response_model=Session)
async def create_session(
    session_data: SessionCreate,
    background_tasks: BackgroundTasks,
    k8s_service: KubernetesService = Depends(get_kubernetes_service),
):
    """Create a new chat session and start a Kubernetes job."""
    session_id = str(uuid.uuid4())

    try:
        job_name = k8s_service.create_job(
            session_id=session_id,
            session_name=session_data.name,
            prompt=session_data.prompt,
            character_id=session_data.character_id,
            token=session_data.token,
        )

        session = {
            "id": session_id,
            "name": session_data.name,
            "status": "Pending",
            "created": datetime.now().isoformat(),
            "jobName": job_name,
            "prompt": session_data.prompt,
        }

        sessions_store[session_id] = session

        return session
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create session: {str(e)}"
        )


@router.get("", response_model=List[Session])
async def list_sessions(
    k8s_service: KubernetesService = Depends(get_kubernetes_service),
):
    """List all chat sessions."""
    # Update session statuses
    for session_id, session in sessions_store.items():
        session["status"] = k8s_service.get_job_status(session["jobName"])

    return list(sessions_store.values())


@router.get("/{session_id}", response_model=Session)
async def get_session(
    session_id: str, k8s_service: KubernetesService = Depends(get_kubernetes_service)
):
    """Get a specific session."""
    if session_id not in sessions_store:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions_store[session_id]
    session["status"] = k8s_service.get_job_status(session["jobName"])

    return session


@router.get("/{session_id}/logs", response_model=JobLogs)
async def get_session_logs(
    session_id: str, k8s_service: KubernetesService = Depends(get_kubernetes_service)
):
    """Get logs for a specific session and trigger webhook on completion."""
    if session_id not in sessions_store:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions_store[session_id]
    status = k8s_service.get_job_status(session["jobName"])
    logs, log_path, log_content = k8s_service.get_pod_logs_with_path(session_id)

    # Send webhook if job completed and not yet notified
    if status == "Completed" and not session.get("webhook_sent"):
        await send_webhook(
            session_id, session["jobName"], status, log_path, logs, log_content
        )
        sessions_store[session_id]["webhook_sent"] = True

    return {"logs": logs, "status": status}


@router.get("/{session_id}/result", response_model=JobResult)
async def get_session_result(
    session_id: str, k8s_service: KubernetesService = Depends(get_kubernetes_service)
):
    """Get complete job result including file content."""
    if session_id not in sessions_store:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions_store[session_id]
    status = k8s_service.get_job_status(session["jobName"])

    # Try to get from stored result first
    if "result" in session and session["result"].get("file_content"):
        return {
            "session_id": session_id,
            "status": status,
            "log_path": session["result"].get("log_path"),
            "pod_logs": session["result"].get("pod_logs"),
            "file_content": session["result"].get("file_content"),
            "file_size": len(session["result"].get("file_content", "")),
        }

    # Fetch fresh logs
    logs, log_path, log_content = k8s_service.get_pod_logs_with_path(session_id)

    return {
        "session_id": session_id,
        "status": status,
        "log_path": log_path,
        "pod_logs": logs,
        "file_content": log_content,
        "file_size": len(log_content) if log_content else 0,
    }


@router.get("/{session_id}/file")
async def get_session_file(
    session_id: str,
    format: str = "json",
    k8s_service: KubernetesService = Depends(get_kubernetes_service),
):
    """Get the output file content from completed job."""
    if session_id not in sessions_store:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions_store[session_id]
    status = k8s_service.get_job_status(session["jobName"])

    if status != "Completed":
        raise HTTPException(
            status_code=400, detail=f"Job not completed yet. Status: {status}"
        )

    # Try to get from stored result first
    if "result" in session and session["result"].get("file_content"):
        file_content = session["result"]["file_content"]
    else:
        # Fetch fresh logs
        logs, log_path, file_content = k8s_service.get_pod_logs_with_path(session_id)

    if not file_content:
        raise HTTPException(status_code=404, detail="No output file found")

    if format == "raw":
        return PlainTextResponse(content=file_content)

    # Return as JSON (parse if it's JSONL)
    try:
        lines = [
            json.loads(line)
            for line in file_content.strip().split("\n")
            if line.strip()
        ]
        return {"data": lines, "count": len(lines)}
    except Exception:
        return {"data": file_content, "format": "text"}


@router.delete("/{session_id}")
async def delete_session(
    session_id: str, k8s_service: KubernetesService = Depends(get_kubernetes_service)
):
    """Delete a session and its associated Kubernetes job."""
    if session_id not in sessions_store:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions_store[session_id]
    job_name = session["jobName"]

    try:
        # Delete the job
        k8s_service.delete_job(job_name)

        # Remove from store
        del sessions_store[session_id]

        return {"message": "Session deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete session: {str(e)}"
        )

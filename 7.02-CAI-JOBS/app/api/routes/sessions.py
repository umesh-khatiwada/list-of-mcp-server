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
    logger.info("Received request to create session")
    session_id = str(uuid.uuid4())

    try:
        job_name = k8s_service.create_job(
            session_id=session_id,
            session_name=session_data.name,
            prompt=session_data.prompt,
            character_id=session_data.character_id,
            token=session_data.token,
            mcp_servers=session_data.mcp_servers,
            workspace_path=session_data.workspace_path,
        )

        session = {
            "id": session_id,
            "name": session_data.name,
            "status": "Pending",
            "created": datetime.now().isoformat(),
            "jobName": job_name,
            "prompt": session_data.prompt,
            "workspace_path": session_data.workspace_path,
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
    logger.info("Received request to list sessions")
    valid_sessions = []

    # Update session statuses (legacy sessions only; skip advanced records without jobName/prompt)
    for session_id, session in sessions_store.items():
        job_name = session.get("jobName")
        job_names = session.get("job_names", [])
        prompt = session.get("prompt")
        
        if job_name and prompt:
            # Legacy session
            session["status"] = k8s_service.get_job_status(job_name)
            valid_sessions.append(session)
        elif job_names and prompt:
            # Advanced session, show as basic with first job
            session_copy = session.copy()
            session_copy["jobName"] = job_names[0] if job_names else ""
            session_copy["status"] = k8s_service.get_manifestwork_status(job_names[0]) if job_names else "Unknown"
            valid_sessions.append(session_copy)
        # Skip sessions without proper job info

    return valid_sessions


@router.get("/{session_id}", response_model=Session)
async def get_session(
    session_id: str, k8s_service: KubernetesService = Depends(get_kubernetes_service)
):
    """Get a specific session."""
    logger.info(f"Received request to get session: {session_id}")
    if session_id not in sessions_store:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions_store[session_id]
    if "jobName" not in session or "prompt" not in session:
        # Advanced sessions are exposed via /api/v2/sessions
        raise HTTPException(status_code=404, detail="Session not found")

    session["status"] = k8s_service.get_job_status(session["jobName"])

    return session


@router.get("/{session_id}/logs", response_model=JobLogs)
async def get_session_logs(
    session_id: str, k8s_service: KubernetesService = Depends(get_kubernetes_service)
):
    """Get logs for a specific session and trigger webhook on completion."""
    logger.info(f"Received request to get session logs: {session_id}")
    if session_id not in sessions_store:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions_store[session_id]
    if "jobName" not in session:
        raise HTTPException(status_code=404, detail="Session not found")

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
    logger.info(f"Received request to get session result: {session_id}")
    if session_id not in sessions_store:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions_store[session_id]
    if "jobName" not in session:
        raise HTTPException(status_code=404, detail="Session not found")

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
    logger.info(f"Received request to get session file: {session_id}")
    if session_id not in sessions_store:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions_store[session_id]
    if "jobName" not in session:
        raise HTTPException(status_code=404, detail="Session not found")

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


@router.get("/jobs")
async def list_jobs(k8s_service: KubernetesService = Depends(get_kubernetes_service)):
    """List all Kubernetes jobs."""
    logger.info("Received request to list jobs")
    try:
        jobs = k8s_service.list_jobs()
        return [
            {
                "name": job.metadata.name,
                "namespace": job.metadata.namespace,
                "status": k8s_service.get_job_status(job.metadata.name),
                "created": job.metadata.creation_timestamp.isoformat() if job.metadata.creation_timestamp else None,
                "labels": job.metadata.labels or {},
            }
            for job in jobs
        ]
    except Exception as e:
        logger.error(f"Failed to list jobs: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{session_id}")
async def delete_session(
    session_id: str, k8s_service: KubernetesService = Depends(get_kubernetes_service)
):
    """Delete a session and its associated Kubernetes job."""
    logger.info(f"Received request to delete session: {session_id}")
    if session_id not in sessions_store:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions_store[session_id]
    if "jobName" not in session:
        raise HTTPException(status_code=404, detail="Session not found")

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


@router.get("/{session_id}/manifest")
async def get_session_manifest(
    session_id: str, k8s_service: KubernetesService = Depends(get_kubernetes_service)
):
    """Get the manifest (e.g., job YAML or ManifestWork spec) for a session."""
    logger.info(f"Received request to get session manifest: {session_id}")
    if session_id not in sessions_store:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions_store[session_id]
    job_name = session.get("jobName") or (session.get("job_names", [])[0] if session.get("job_names") else None)
    if not job_name:
        raise HTTPException(status_code=404, detail="No job associated with session")

    try:
        manifest = k8s_service.get_manifest(job_name)
        return {"manifest": manifest}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get manifest: {str(e)}")

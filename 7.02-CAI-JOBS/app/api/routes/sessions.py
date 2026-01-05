"""Session management routes."""
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

import requests
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse

from ...api.dependencies import get_kubernetes_service
from ...config import settings
from ...models import JobLogs, JobResult, Session, SessionCreate
from ...services import send_webhook
from ...services.kubernetes_service import KubernetesService
from ...services.session_store import sessions_store, save_sessions
import asyncio
import websockets

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
        save_sessions()

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
    """Get logs for a specific session from Loki and trigger webhook on completion."""
    logger.info(f"Received request to get session logs: {session_id}")
    logger.info(f"Sessions in store: {list(sessions_store.keys())}")
    if session_id not in sessions_store:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions_store[session_id]
    if "jobName" in session:
        status = k8s_service.get_job_status(session["jobName"])

        # Fetch logs from Loki if configured
        job_name = session["jobName"]
        logs_str = ""

        # Only query Loki if configured
        if settings.loki_url:
            loki_url = settings.loki_url.rstrip('/')

            # Try to get the pod name and labels from Kubernetes
            pod_name = None
            job_label_name = None
            try:
                pods = k8s_service.core_v1.list_namespaced_pod(
                    namespace=k8s_service.namespace, label_selector=f"session-id={session_id}"
                )
                if pods.items:
                    pod = pods.items[0]
                    pod_name = pod.metadata.name
                    # Get job-name from pod labels (Kubernetes adds this automatically)
                    if pod.metadata.labels:
                        job_label_name = pod.metadata.labels.get("job-name") or pod.metadata.labels.get("job_name")
                    logger.info(f"Found pod {pod_name} for job {job_name}, job-label: {job_label_name}")
            except Exception as e:
                logger.info(f"Failed to get pod name: {e}")

            # Calculate time range in nanoseconds
            start_ns = int((datetime.now() - timedelta(hours=1)).timestamp() * 1e9)
            end_ns = int(datetime.now().timestamp() * 1e9)

            # Build label candidates - prioritize exact matches, then regex
            label_candidates = []
            
            # Most specific: exact pod name match
            if pod_name:
                label_candidates.append(('pod_exact', f'{{pod="{pod_name}"}}'))
            
            # Job name from pod labels (Kubernetes standard)
            if job_label_name:
                label_candidates.append(('job_name_exact', f'{{job_name="{job_label_name}"}}'))
                label_candidates.append(('job_name_regex', f'{{job_name=~"{job_label_name}.*"}}'))
            
            # Pod name regex matching job pattern (pods are named {job-name}-{random})
            if pod_name:
                # Extract base job name from pod (remove random suffix)
                pod_base = pod_name.rsplit('-', 1)[0] if '-' in pod_name else pod_name
                label_candidates.append(('pod_regex', f'{{pod=~"{pod_base}-.*"}}'))
            
            # Job name regex
            label_candidates.append(('job_name_job_regex', f'{{job_name=~"{job_name}.*"}}'))
            
            # Session ID based queries
            session_id_short = session_id[:8]
            label_candidates.append(('session_id', f'{{session_id="{session_id}"}}'))
            label_candidates.append(('pod_session_regex', f'{{pod=~".*{session_id_short}.*"}}'))
            
            # Namespace + app label combination
            label_candidates.append(('namespace_app', f'{{namespace="{k8s_service.namespace}",app="cai-chat"}}'))
            
            # Generic namespace (less specific, try last)
            label_candidates.append(('namespace_only', f'{{namespace="{k8s_service.namespace}"}}'))

            # Try each label candidate
            for label_name, q in label_candidates:
                try:
                    params = {
                        "query": q,
                        "limit": 500,  # Increased limit for better coverage
                        "direction": "backward",
                        "start": start_ns,
                        "end": end_ns,
                    }
                    logger.info(f"Querying Loki for session {session_id} (job: {job_name}) trying label {label_name} query={q}")
                    loki_endpoint = f"{loki_url}/loki/api/v1/query_range"
                    res = requests.get(loki_endpoint, params=params, timeout=15)
                    logger.info(f"Loki response for label {label_name}: status={res.status_code}")
                    
                    if not res.ok:
                        logger.warning(f"Loki query failed with status {res.status_code}: {res.text[:200]}")
                        continue
                    
                    data = res.json().get("data", {})
                    result_streams = data.get("result", [])
                    
                    if not result_streams:
                        logger.debug(f"No streams found for label {label_name}")
                        continue
                    
                    # Collect logs from all streams
                    logs = []
                    for stream in result_streams:
                        stream_labels = stream.get("stream", {})
                        for v in stream.get("values", []):
                            logs.append(v[1])
                    
                    if not logs:
                        logger.debug(f"No log entries found for label {label_name}")
                        continue
                    
                    # Reverse logs to get chronological order (oldest first)
                    logs_str = "\n".join(reversed(logs))
                    logger.info(f"Retrieved {len(logs)} log lines from Loki using label {label_name}")
                    break  # Use the first successful one
                    
                except requests.exceptions.RequestException as le_inner:
                    logger.warning(f"Loki request failed for label {label_name}: {le_inner}")
                    continue
                except Exception as le_inner:
                    logger.warning(f"Loki attempt for label {label_name} failed: {le_inner}")
                    continue

        # Fallback to Kubernetes logs if Loki not configured or no logs found
        if not logs_str:
            if not settings.loki_url:
                logger.info("Loki not configured, using Kubernetes logs")
            else:
                logger.info("No logs found in Loki, falling back to Kubernetes logs")
            
            try:
                logs, _, _ = k8s_service.get_pod_logs_with_path(session_id)
                logs_str = logs if logs else "No logs available"
            except Exception as e:
                logger.error(f"Fallback to K8s logs failed: {e}")
                logs_str = "No logs available"

        # For webhook, we need log_path and log_content, but since we're using Loki, set to None or extract
        log_path = None
        log_content = None
        # Try to extract from logs
        for line in logs_str.split('\n'):
            if 'LOG_FILE_PATH:' in line:
                log_path = line.replace('LOG_FILE_PATH:', '').strip()
                break

        # Send webhook if job completed and not yet notified
        if status == "Completed" and not session.get("webhook_sent"):
            await send_webhook(
                session_id, job_name, status, log_path, logs_str, log_content
            )
            sessions_store[session_id]["webhook_sent"] = True
            save_sessions()

        return {"logs": logs_str, "status": status}

    elif "job_names" in session:
        # Advanced session with multiple jobs - handle similar to advanced sessions route
        job_names = session.get("job_names", [])
        if not job_names:
            raise HTTPException(status_code=404, detail="No jobs found for this session")

        # Get status - try to determine from progress if available
        try:
            # Try to get status from first job's ManifestWork status
            status = k8s_service.get_manifestwork_status(job_names[0]) if job_names else "Unknown"
        except Exception as e:
            logger.warning(f"Failed to get ManifestWork status: {e}")
            status = "Unknown"

        # Fetch logs from all jobs with improved error handling
        all_logs = []
        log_path = None
        log_content = None
        
        for job_name in job_names:
            try:
                # Use get_manifestwork_logs for ManifestWork-based jobs
                logs, job_log_path, job_log_content = k8s_service.get_manifestwork_logs(job_name)
                if logs:
                    all_logs.append(f"=== Logs for {job_name} ===\n{logs}")
                elif job_log_path:
                    all_logs.append(f"=== Logs for {job_name} ===\nLog path: {job_log_path}\n(Content not available)")
                
                # Capture first available log_path and log_content
                if not log_path and job_log_path:
                    log_path = job_log_path
                if not log_content and job_log_content:
                    log_content = job_log_content
                    
            except Exception as e:
                logger.warning(f"Failed to get logs for job {job_name}: {e}")
                # Try fallback: get logs directly from pods
                try:
                    pods = k8s_service.core_v1.list_namespaced_pod(
                        namespace=k8s_service.namespace,
                        label_selector=f"session-id={session_id}",
                    )
                    for pod in pods.items:
                        if job_name in pod.metadata.name or session_id[:8] in pod.metadata.name:
                            pod_logs = k8s_service.core_v1.read_namespaced_pod_log(
                                name=pod.metadata.name,
                                namespace=k8s_service.namespace,
                                tail_lines=200
                            )
                            all_logs.append(f"=== Logs for {job_name} (pod: {pod.metadata.name}) ===\n{pod_logs}")
                            break
                except Exception as e2:
                    logger.warning(f"Fallback log retrieval also failed for {job_name}: {e2}")
                    all_logs.append(f"=== Logs for {job_name} ===\nError retrieving logs: {str(e)}")

        logs_str = "\n\n".join(all_logs) if all_logs else "No logs found"

        # Send webhook if completed (similar to advanced sessions)
        if status == "Completed" and not session.get("webhook_sent"):
            await send_webhook(
                session_id, job_names[0] if job_names else "", status, log_path, logs_str, log_content
            )
            sessions_store[session_id]["webhook_sent"] = True
            save_sessions()

        return {"logs": logs_str, "status": status}

    else:
        raise HTTPException(status_code=404, detail="Session not found")


@router.websocket("/{session_id}/logs/ws")
async def get_session_logs_ws(
    websocket: WebSocket,
    session_id: str,
    query: Optional[str] = None,
    k8s_service: KubernetesService = Depends(get_kubernetes_service),
):
    """Stream logs for a specific session via WebSocket from Loki."""
    await websocket.accept()
    logger.info(f"WebSocket connection accepted for session: {session_id}")

    if session_id not in sessions_store:
        await websocket.send_json({"error": "Session not found"})
        await websocket.close()
        return

    session = sessions_store[session_id]
    job_name = session.get("jobName") or (session.get("job_names", [])[0] if session.get("job_names") else None)

    if not job_name:
        await websocket.send_json({"error": "No job associated with session"})
        await websocket.close()
        return

    if not settings.loki_url:
        await websocket.send_json({"error": "Loki not configured for live logs"})
        await websocket.close()
        return

    # Construct Loki query if not provided
    if not query:
        session_id_short = session_id[:8]
        # Query by pod regex (matches cai-job-XXXXXXXX-...)
        query = f'{{pod=~".*{session_id_short}.*"}}'
        logger.info(f"Defaulting to LogQL query: {query}")

    loki_ws_url = f"{settings.loki_ws_url}?query={query}"

    async def heartbeat():
        """Send periodic status updates to keep connection alive and update UI."""
        try:
            while True:
                await asyncio.sleep(15)
                try:
                    current_status = k8s_service.get_job_status(job_name) if "jobName" in session else k8s_service.get_manifestwork_status(job_name)
                    await websocket.send_json({"heartbeat": True, "status": current_status, "timestamp": datetime.now().isoformat()})
                except Exception as e:
                    logger.debug(f"Heartbeat send failed: {e}")
                    break
        except asyncio.CancelledError:
            pass

    try:
        current_status = k8s_service.get_job_status(job_name) if "jobName" in session else k8s_service.get_manifestwork_status(job_name)
        await websocket.send_json({
            "info": "Connected to logs proxy",
            "status": current_status,
            "session_id": session_id,
            "job_name": job_name
        })

        async with websockets.connect(loki_ws_url) as loki_ws:
            logger.info(f"Connected to Loki WebSocket: {loki_ws_url}")
            
            # Start heartbeat task
            heartbeat_task = asyncio.create_task(heartbeat())
            
            try:
                while True:
                    # Receive from Loki
                    loki_msg = await loki_ws.recv()
                    data = json.loads(loki_msg)
                    
                    # Loki streams returns multiple lines sometimes
                    if "streams" in data:
                        for stream in data.get("streams", []):
                            for ts, line in stream.get("values", []):
                                current_status = k8s_service.get_job_status(job_name) if "jobName" in session else k8s_service.get_manifestwork_status(job_name)
                                await websocket.send_json({
                                    "timestamp": ts,
                                    "line": line,
                                    "status": current_status
                                })
                    else:
                        # Raw stream message fallback
                        await websocket.send_json(data)
            except (WebSocketDisconnect, websockets.exceptions.ConnectionClosed):
                logger.info("WebSocket connection closed")
            finally:
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass
    except Exception as e:
        logger.error(f"Failed to connect to Loki WebSocket: {e}")
        await websocket.send_json({"error": f"Failed to connect to Loki: {str(e)}"})
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


@router.get("/{session_id}/result", response_model=JobResult)
async def get_session_result(
    session_id: str, k8s_service: KubernetesService = Depends(get_kubernetes_service)
):
    """Get complete job result including file content."""
    logger.info(f"Received request to get session result: {session_id}")
    if session_id not in sessions_store:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions_store[session_id]
    logger.info(f"Session: {session}")
    job_name = session.get("jobName")
    if not job_name and session.get("job_names"):
        # Advanced session, job name is cai-job-{session_id[:8]}
        job_name = f"cai-job-{session_id[:8]}"
    if not job_name:
        raise HTTPException(status_code=404, detail="Session not found")

    status = k8s_service.get_job_status(job_name)

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
        save_sessions()

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

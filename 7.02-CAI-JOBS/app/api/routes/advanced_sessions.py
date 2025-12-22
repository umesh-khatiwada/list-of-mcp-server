"""Advanced session management routes with CAI features."""
import logging
import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse

from ...models.advanced import AdvancedSessionCreate, SessionMode, SessionStatus
from ...services.advanced_kubernetes_service import AdvancedKubernetesService
from ...services.session_store import sessions_store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2/sessions", tags=["advanced-sessions"])


def get_advanced_kubernetes_service() -> AdvancedKubernetesService:
    """Get Advanced Kubernetes service instance."""
    return AdvancedKubernetesService()


@router.post("", response_model=SessionStatus)
async def create_advanced_session(
    session_data: AdvancedSessionCreate,
    background_tasks: BackgroundTasks,
    k8s_service: AdvancedKubernetesService = Depends(get_advanced_kubernetes_service),
):
    """Create an advanced CAI session with multiple execution modes."""
    session_id = str(uuid.uuid4())

    try:
        # Create advanced session
        job_names, mode = k8s_service.create_advanced_session(session_id, session_data)

        # Create enhanced session record
        session = {
            "id": session_id,
            "name": session_data.name,
            "mode": mode,
            "status": "Pending",
            "created": datetime.now().isoformat(),
            "job_names": job_names,
            "current_step": "Initializing",
            "total_steps": len(job_names) if mode == SessionMode.PARALLEL else None,
            "completed_steps": 0,
            "estimated_cost": session_data.cost_constraints.price_limit,
            "actual_cost": 0.0,
            "cost_limit": session_data.cost_constraints.price_limit,
            "outputs": {},
            "flags_found": [],
            "vulnerabilities": [],
            "original_config": session_data.dict(),
        }

        sessions_store[session_id] = session

        # Create response
        return SessionStatus(**session)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to create advanced session: {str(e)}"
        )


@router.get("", response_model=List[SessionStatus])
async def list_advanced_sessions(
    mode: SessionMode = Query(None, description="Filter by session mode"),
    k8s_service: AdvancedKubernetesService = Depends(get_advanced_kubernetes_service),
):
    """List all advanced sessions with optional filtering."""
    enhanced_sessions = []

    for session_id, session in sessions_store.items():
        # Skip if mode filter doesn't match
        if mode and session.get("mode") != mode:
            continue

        # Ensure required fields for advanced schema
        session.setdefault("mode", SessionMode.SINGLE)
        session.setdefault("job_names", [session.get("jobName", "")])
        session.setdefault("created", session.get("created", ""))

        # Update session status
        if "job_names" in session:
            # Multi-job session
            progress = k8s_service.get_session_progress(session_id)
            session["completed_steps"] = progress.get("completed_jobs", 0)
            session["status"] = _determine_session_status(progress)
        else:
            # Legacy single job session
            session["status"] = k8s_service.get_job_status(session.get("jobName", ""))

        enhanced_sessions.append(SessionStatus(**session))

    return enhanced_sessions


@router.get("/{session_id}", response_model=SessionStatus)
async def get_advanced_session(
    session_id: str,
    k8s_service: AdvancedKubernetesService = Depends(get_advanced_kubernetes_service),
):
    """Get detailed information about a specific advanced session."""
    if session_id not in sessions_store:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions_store[session_id]

    # Ensure required fields exist (migration for old sessions)
    if "mode" not in session:
        session["mode"] = "single"
    if "job_names" not in session:
        # Try to infer from jobName (legacy field)
        if "jobName" in session:
            session["job_names"] = [session["jobName"]]
        else:
            session["job_names"] = []

    # Update progress for multi-job sessions
    if len(session.get("job_names", [])) > 0:
        progress = k8s_service.get_session_progress(session_id)
        session["completed_steps"] = progress.get("completed_jobs", 0)
        session["status"] = _determine_session_status(progress)

        # Update detailed progress
        session["progress_details"] = progress
    else:
        # No jobs found
        session["status"] = "Unknown"

    return SessionStatus(**session)


@router.get("/{session_id}/progress")
async def get_session_progress(
    session_id: str,
    k8s_service: AdvancedKubernetesService = Depends(get_advanced_kubernetes_service),
):
    """Get detailed progress information for a session."""
    if session_id not in sessions_store:
        raise HTTPException(status_code=404, detail="Session not found")

    progress = k8s_service.get_session_progress(session_id)
    return progress


@router.get("/{session_id}/results")
async def get_session_results(
    session_id: str,
    include_logs: bool = Query(True, description="Include full logs"),
    k8s_service: AdvancedKubernetesService = Depends(get_advanced_kubernetes_service),
):
    """Get comprehensive results from all jobs in a session."""
    if session_id not in sessions_store:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions_store[session_id]

    # Check if session is complete
    if "job_names" in session:
        progress = k8s_service.get_session_progress(session_id)
        status = _determine_session_status(progress)
        if status not in ["Completed", "Failed"]:
            return {
                "status": status,
                "message": "Session still running",
                "progress": progress,
            }

    # Extract results
    results = k8s_service.extract_session_results(session_id)

    if not include_logs:
        # Remove detailed logs to reduce response size
        if "outputs" in results:
            results["outputs"] = {
                agent: f"Logs available (length: {len(logs)} chars)"
                for agent, logs in results["outputs"].items()
            }

    # Update session store with results
    sessions_store[session_id].update(
        {
            "flags_found": results.get("flags_found", []),
            "vulnerabilities": results.get("vulnerabilities", []),
            "outputs": results.get("outputs", {}),
        }
    )

    return results


@router.get("/{session_id}/flags")
async def get_session_flags(
    session_id: str,
    k8s_service: AdvancedKubernetesService = Depends(get_advanced_kubernetes_service),
):
    """Get all CTF flags found in a session."""
    if session_id not in sessions_store:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions_store[session_id]

    # If flags already extracted, return them
    if "flags_found" in session and session["flags_found"]:
        return {"flags": session["flags_found"]}

    # Extract flags from current results
    results = k8s_service.extract_session_results(session_id)
    flags = results.get("flags_found", [])

    # Update session store
    sessions_store[session_id]["flags_found"] = flags

    return {"flags": flags, "count": len(flags)}

@router.delete("/{session_id}")
async def delete_advanced_session(
    session_id: str,
    k8s_service: AdvancedKubernetesService = Depends(get_advanced_kubernetes_service),
):
    """Delete an advanced session and all associated jobs."""

    if session_id not in sessions_store:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions_store[session_id]

    try:
        # Delete all jobs tied to this session
        job_names = session.get("job_names") or ([session.get("jobName")] if session.get("jobName") else [])
        for job_name in job_names:
            if job_name:
                k8s_service.delete_job(job_name)

        # Remove session from store
        del sessions_store[session_id]

        return {"message": "Advanced session deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete advanced session: {str(e)}"
        )


@router.get("/{session_id}/vulnerabilities")
async def get_session_vulnerabilities(
    session_id: str,
    k8s_service: AdvancedKubernetesService = Depends(get_advanced_kubernetes_service),
):
    """Get all vulnerabilities found in a session."""
    if session_id not in sessions_store:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions_store[session_id]

    # If vulnerabilities already extracted, return them
    if "vulnerabilities" in session and session["vulnerabilities"]:
        return {"vulnerabilities": session["vulnerabilities"]}

    # Extract vulnerabilities from current results
    results = k8s_service.extract_session_results(session_id)
    vulnerabilities = results.get("vulnerabilities", [])

    # Update session store
    sessions_store[session_id]["vulnerabilities"] = vulnerabilities

    return {"vulnerabilities": vulnerabilities, "count": len(vulnerabilities)}


@router.get("/{session_id}/agent/{agent_alias}/logs")
async def get_agent_logs(
    session_id: str,
    agent_alias: str,
    k8s_service: AdvancedKubernetesService = Depends(get_advanced_kubernetes_service),
):
    """Get logs from a specific agent in a parallel session."""
    if session_id not in sessions_store:
        raise HTTPException(status_code=404, detail="Session not found")

    try:
        # Find pods with specific agent alias
        pods = k8s_service.core_v1.list_namespaced_pod(
            namespace=k8s_service.namespace,
            label_selector=f"session-id={session_id},agent-alias={agent_alias}",
        )

        if not pods.items:
            raise HTTPException(
                status_code=404,
                detail=f"No pods found for agent '{agent_alias}' in session '{session_id}'",
            )

        # Get logs from the first matching pod
        pod_name = pods.items[0].metadata.name
        logs = k8s_service.core_v1.read_namespaced_pod_log(
            name=pod_name, namespace=k8s_service.namespace, tail_lines=200
        )

        return {"agent": agent_alias, "logs": logs}

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get logs for agent '{agent_alias}': {str(e)}",
        )


@router.post("/{session_id}/stop")
async def stop_session(
    session_id: str,
    k8s_service: AdvancedKubernetesService = Depends(get_advanced_kubernetes_service),
):
    """Stop a running session by deleting all associated jobs."""
    if session_id not in sessions_store:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions_store[session_id]

    try:
        job_names = session.get("job_names", [session.get("jobName")])
        deleted_jobs = []

        for job_name in job_names:
            if job_name:
                k8s_service.delete_job(job_name)
                deleted_jobs.append(job_name)

        # Update session status
        sessions_store[session_id]["status"] = "Stopped"
        sessions_store[session_id]["current_step"] = "Stopped by user"

        return {"message": "Session stopped successfully", "deleted_jobs": deleted_jobs}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop session: {str(e)}")


@router.delete("/{session_id}")
async def delete_advanced_session(
    session_id: str,
    k8s_service: AdvancedKubernetesService = Depends(get_advanced_kubernetes_service),
):
    """Delete an advanced session and all associated jobs."""
    if session_id not in sessions_store:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions_store[session_id]

    try:
        # Delete all jobs
        job_names = session.get("job_names", [session.get("jobName")])
        deleted_jobs = []

        for job_name in job_names:
            if job_name:
                k8s_service.delete_job(job_name)
                deleted_jobs.append(job_name)

        # Remove from store
        del sessions_store[session_id]

        return {
            "message": "Advanced session deleted successfully",
            "deleted_jobs": deleted_jobs,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete session: {str(e)}"
        )


@router.get("/{session_id}/export")
async def export_session(
    session_id: str,
    format: str = Query("json", description="Export format: json, yaml, or report"),
    k8s_service: AdvancedKubernetesService = Depends(get_advanced_kubernetes_service),
):
    """Export session data and results in various formats."""
    if session_id not in sessions_store:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions_store[session_id]
    results = k8s_service.extract_session_results(session_id)

    export_data = {
        "session": session,
        "results": results,
        "exported_at": datetime.now().isoformat(),
    }

    if format == "json":
        return export_data
    elif format == "yaml":
        import yaml

        yaml_content = yaml.dump(export_data, default_flow_style=False)
        return PlainTextResponse(content=yaml_content, media_type="text/yaml")
    elif format == "report":
        report = _generate_report(session, results)
        return PlainTextResponse(content=report, media_type="text/plain")
    else:
        raise HTTPException(status_code=400, detail="Unsupported export format")


def _determine_session_status(progress: dict) -> str:
    """Determine overall session status from progress data."""
    total = progress.get("total_jobs", 0)
    completed = progress.get("completed_jobs", 0)
    failed = progress.get("failed_jobs", 0)
    running = progress.get("running_jobs", 0)

    if failed > 0 and completed + failed == total:
        return "Failed"
    elif completed == total:
        return "Completed"
    elif running > 0:
        return "Running"
    else:
        return "Pending"


def _generate_report(session: dict, results: dict) -> str:
    """Generate a human-readable report."""
    lines = [
        f"# CAI Session Report: {session['name']}",
        f"Session ID: {session['id']}",
        f"Created: {session['created']}",
        f"Mode: {session.get('mode', 'unknown')}",
        f"Status: {session.get('status', 'unknown')}",
        "",
        "## Summary",
        f"- Jobs executed: {len(session.get('job_names', []))}"
        f"- Flags found: {len(results.get('flags_found', []))}",
        f"- Vulnerabilities: {len(results.get('vulnerabilities', []))}",
        "",
    ]

    # Flags section
    if results.get("flags_found"):
        lines.extend(["## Flags Found", ""])
        for i, flag in enumerate(results["flags_found"], 1):
            lines.append(f"{i}. {flag}")
        lines.append("")

    # Vulnerabilities section
    if results.get("vulnerabilities"):
        lines.extend(["## Vulnerabilities", ""])
        for i, vuln in enumerate(results["vulnerabilities"], 1):
            lines.append(f"{i}. {vuln}")
        lines.append("")

    # Agent outputs summary
    if results.get("outputs"):
        lines.extend(["## Agent Outputs Summary", ""])
        for agent, output in results["outputs"].items():
            lines.extend(
                [
                    f"### Agent: {agent}",
                    f"Output length: {len(output)} characters",
                    "```",
                    output[:500] + "..." if len(output) > 500 else output,
                    "```",
                    "",
                ]
            )

    return "\n".join(lines)

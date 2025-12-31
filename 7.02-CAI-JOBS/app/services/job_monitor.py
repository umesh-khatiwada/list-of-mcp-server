"""Background tasks for monitoring jobs."""
import asyncio
import logging

from ..api.dependencies import get_kubernetes_service
from ..services import send_webhook
from ..services.session_store import sessions_store, save_sessions

logger = logging.getLogger(__name__)


async def monitor_jobs():
    """Background task to monitor job completions and send webhooks."""
    k8s_service = get_kubernetes_service()

    while True:
        try:
            await asyncio.sleep(10)  # Check every 10 seconds

            for session_id, session in list(sessions_store.items()):
                if session.get("webhook_sent"):
                    continue

                # Handle both legacy single-job and advanced multi-job sessions
                if "job_names" in session:
                    # Advanced session with multiple jobs
                    job_names = session["job_names"]
                    all_completed = True
                    all_statuses = []
                    
                    for job_name in job_names:
                        status = k8s_service.get_manifestwork_status(job_name)
                        all_statuses.append(status)
                        logger.info(f"ManifestWork {job_name} status: {status}")
                        if status not in ["Completed", "Failed"]:
                            all_completed = False
                    
                    # Update session status
                    status_changed = False
                    if all(s == "Completed" for s in all_statuses):
                        if session.get("status") != "Completed":
                            session["status"] = "Completed"
                            status_changed = True
                    elif any(s == "Failed" for s in all_statuses):
                        if session.get("status") != "Failed":
                            session["status"] = "Failed"
                            status_changed = True
                    else:
                        if session.get("status") != "Running":
                            session["status"] = "Running"
                            status_changed = True
                    
                    # Save if status changed
                    if status_changed:
                        save_sessions()
                    
                    # Send webhook when all jobs complete
                    if all_completed:
                        logger.info(
                            f"ManifestWork {job_names} completed with statuses: {all_statuses}"
                        )

                        # Fetch logs for multi-job session
                        all_logs = []
                        for job_name in job_names:
                            logs, log_path, log_content = k8s_service.get_manifestwork_logs(job_name)
                            if logs:
                                all_logs.append(f"=== Logs for {job_name} ===\n{logs}")

                        combined_logs = "\n\n".join(all_logs) if all_logs else f"Multi-job session completed with statuses: {all_statuses}"

                        await send_webhook(
                            session_id,
                            job_names[0],
                            session["status"],
                            None,
                            combined_logs,
                            None,
                        )
                        sessions_store[session_id]["webhook_sent"] = True
                        save_sessions()
                
                elif "jobName" in session:
                    # Legacy single-job session
                    status = k8s_service.get_job_status(session["jobName"])
                    status_changed = session.get("status") != status
                    session["status"] = status
                    
                    # Save if status changed
                    if status_changed:
                        save_sessions()

                    # Send webhook when job completes
                    if status in ["Completed", "Failed"]:
                        logger.info(
                            f"Job {session['jobName']} completed with status: {status}"
                        )
                        logs, log_path, log_content = k8s_service.get_pod_logs_with_path(
                            session_id
                        )
                        await send_webhook(
                            session_id,
                            session["jobName"],
                            status,
                            log_path,
                            logs,
                            log_content,
                        )
                        sessions_store[session_id]["webhook_sent"] = True
                        save_sessions()

        except Exception as e:
            logger.error(f"Error in job monitor: {str(e)}")
            await asyncio.sleep(5)

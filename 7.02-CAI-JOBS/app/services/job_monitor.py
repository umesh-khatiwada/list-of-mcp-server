"""Background tasks for monitoring jobs."""
import asyncio
import logging

from ..api.dependencies import get_kubernetes_service
from ..services import send_webhook
from ..services.session_store import sessions_store

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
                        status = k8s_service.get_job_status(job_name)
                        all_statuses.append(status)
                        if status not in ["Completed", "Failed"]:
                            all_completed = False
                    
                    # Update session status
                    if all(s == "Completed" for s in all_statuses):
                        session["status"] = "Completed"
                    elif any(s == "Failed" for s in all_statuses):
                        session["status"] = "Failed"
                    else:
                        session["status"] = "Running"
                    
                    # Send webhook when all jobs complete
                    if all_completed:
                        logger.info(
                            f"Job {job_names[0]} completed with status: {session['status']}"
                        )
                        await send_webhook(
                            session_id,
                            job_names[0],
                            session["status"],
                            None,
                            f"Multi-job session completed with statuses: {all_statuses}",
                            None,
                        )
                        sessions_store[session_id]["webhook_sent"] = True
                
                elif "jobName" in session:
                    # Legacy single-job session
                    status = k8s_service.get_job_status(session["jobName"])
                    session["status"] = status

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

        except Exception as e:
            logger.error(f"Error in job monitor: {str(e)}")
            await asyncio.sleep(5)

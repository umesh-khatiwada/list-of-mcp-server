"""Webhook service for handling job completion notifications."""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional

import requests

from ..config import settings

logger = logging.getLogger(__name__)

# Thread pool for async webhook sending
webhook_executor = ThreadPoolExecutor(max_workers=settings.webhook_max_workers)


def _send_webhook_sync(
    session_id: str,
    job_name: str,
    status: str,
    log_path: Optional[str] = None,
    logs_content: Optional[str] = None,
    file_content: Optional[str] = None,
) -> None:
    """Send webhook notification synchronously (runs in thread pool).

    Args:
        session_id: The session ID
        job_name: The Kubernetes job name
        status: The job status
        log_path: Optional path to log file
        logs_content: Optional log content
        file_content: Optional file content
    """
    if not settings.webhook_url:
        logger.info(
            f"No webhook URL configured, skipping notification for session {session_id}"
        )
        return

    try:
        payload = {
            "session_id": session_id,
            "job_name": job_name,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "log_path": log_path,
            "pod_logs": logs_content,
            "file_content": file_content,
        }

        response = requests.post(settings.webhook_url, json=payload, timeout=30)
        logger.info(f"Webhook sent for session {session_id}: {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to send webhook for session {session_id}: {str(e)}")


async def send_webhook(
    session_id: str,
    job_name: str,
    status: str,
    log_path: Optional[str] = None,
    logs_content: Optional[str] = None,
    file_content: Optional[str] = None,
) -> None:
    """Send webhook notification asynchronously.

    Args:
        session_id: The session ID
        job_name: The Kubernetes job name
        status: The job status
        log_path: Optional path to log file
        logs_content: Optional log content
        file_content: Optional file content
    """
    loop = asyncio.get_event_loop()
    loop.run_in_executor(
        webhook_executor,
        _send_webhook_sync,
        session_id,
        job_name,
        status,
        log_path,
        logs_content,
        file_content,
    )

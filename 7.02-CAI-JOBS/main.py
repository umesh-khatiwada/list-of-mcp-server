import asyncio
import json
import logging
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import List, Optional

import requests
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from kubernetes import client, config
from pydantic import BaseModel

# Thread pool for async webhook sending
webhook_executor = ThreadPoolExecutor(max_workers=5)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="CAI Kubernetes Job Manager")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Kubernetes config
try:
    config.load_incluster_config()  # Use this when running in cluster
except:
    config.load_kube_config()  # Use this for local development

# Kubernetes clients
batch_v1 = client.BatchV1Api()
core_v1 = client.CoreV1Api()

# In-memory session store (use Redis/Database in production)
sessions_store = {}


# Pydantic models
class SessionCreate(BaseModel):
    name: str
    prompt: str
    character_id: Optional[str] = None
    token: Optional[str] = None


class Session(BaseModel):
    id: str
    name: str
    status: str
    created: str
    jobName: str
    prompt: str


class JobLogs(BaseModel):
    logs: str
    status: str


class JobResult(BaseModel):
    session_id: str
    status: str
    log_path: Optional[str] = None
    pod_logs: Optional[str] = None
    file_content: Optional[str] = None
    file_size: Optional[int] = None


# Kubernetes configuration
NAMESPACE = os.getenv("NAMESPACE", "default")
CAI_IMAGE = os.getenv("CAI_IMAGE", "docker.io/neptune1212/cai:amd64")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")  # Optional webhook for job completion


def _send_webhook_sync(
    session_id: str,
    job_name: str,
    status: str,
    log_path: str = None,
    logs_content: str = None,
    file_content: str = None,
):
    """Send webhook notification synchronously (runs in thread pool)"""
    if not WEBHOOK_URL:
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

        response = requests.post(WEBHOOK_URL, json=payload, timeout=30)
        logger.info(f"Webhook sent for session {session_id}: {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to send webhook for session {session_id}: {str(e)}")


async def send_webhook(
    session_id: str,
    job_name: str,
    status: str,
    log_path: str = None,
    logs_content: str = None,
    file_content: str = None,
):
    """Send webhook notification asynchronously"""
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


def sanitize_label(value: str) -> str:
    """Sanitize a string to be used as a Kubernetes label"""
    # Replace spaces and invalid chars with hyphens
    sanitized = value.replace(" ", "-").replace("_", "-")
    # Remove any character that's not alphanumeric, hyphen, or dot
    sanitized = "".join(c for c in sanitized if c.isalnum() or c in ["-", "."])
    # Ensure it starts and ends with alphanumeric
    sanitized = sanitized.strip("-.")
    # Limit to 63 characters (K8s label limit)
    return sanitized[:63]


def create_k8s_job(
    session_id: str,
    session_name: str,
    prompt: str,
    character_id: Optional[str] = None,
    token: Optional[str] = None,
):
    """Create a Kubernetes Job for CAI chat session"""

    job_name = f"cai-job-{session_id[:8]}"
    sanitized_name = sanitize_label(session_name)

    # Environment variables for the CAI container
    env_vars = [
        client.V1EnvVar(name="PROMPT", value=prompt),
        client.V1EnvVar(name="SESSION_ID", value=session_id),
        client.V1EnvVar(
            name="DEEPSEEK_API_KEY", value=os.getenv("DEEPSEEK_API_KEY", "")
        ),
        client.V1EnvVar(name="CAI_MODEL", value="deepseek-chat"),
        client.V1EnvVar(name="OPENAI_API_KEY", value=os.getenv("OPENAI_API_KEY", "")),
        client.V1EnvVar(name="CAI_STEAM", value=os.getenv("CAI_STEAM", "true")),
        client.V1EnvVar(
            name="CAI_AGENT_TYPE", value=os.getenv("CAI_AGENT_TYPE", "offsec_pattern")
        ),
    ]

    if character_id:
        env_vars.append(client.V1EnvVar(name="CHARACTER_ID", value=character_id))
    if token:
        env_vars.append(client.V1EnvVar(name="CAI_TOKEN", value=token))

    # Define the container
    container = client.V1Container(
        name="cai-chat",
        image=CAI_IMAGE,
        env=env_vars,
        image_pull_policy="Always",
        command=["/bin/bash", "-c"],
        args=[
            f"""source /home/kali/cai/bin/activate
cat <<'EOF' >/tmp/cai_commands.txt
{prompt}
EOF

# Execute CAI with agents.yml and piped commands
cat /tmp/cai_commands.txt | cai --yaml /config/agents.yml

# Capture logs
EXIT_CODE=$?
if [ -d /home/kali/logs ]; then
  LOGFILE=$(find /home/kali/logs -name "cai_*.jsonl" -type f 2>/dev/null | head -1)
  if [ -n "$LOGFILE" ]; then
    echo "LOG_FILE_PATH: $LOGFILE"
    echo "$LOGFILE" > /tmp/job_completion_signal
    cat "$LOGFILE" > /tmp/job_logs_content
  fi
fi
exit $EXIT_CODE
"""
        ],
        volume_mounts=[
            client.V1VolumeMount(name="agents-config", mount_path="/config")
        ],
    )

    # Define the pod template
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(
            labels={"app": "cai-chat", "session-id": session_id}
        ),
        spec=client.V1PodSpec(
            restart_policy="Never",
            containers=[container],
            volumes=[
                client.V1Volume(
                    name="agents-config",
                    config_map=client.V1ConfigMapVolumeSource(name="cai-agents-config"),
                )
            ],
        ),
    )

    # Define the job
    job = client.V1Job(
        api_version="batch/v1",
        kind="Job",
        metadata=client.V1ObjectMeta(
            name=job_name,
            labels={
                "session-id": session_id,
                "session-name": sanitized_name,
                "app": "cai-chat",
            },
        ),
        spec=client.V1JobSpec(
            template=template,
            backoff_limit=3,
            ttl_seconds_after_finished=3600,  # Clean up after 1 hour
        ),
    )

    try:
        batch_v1.create_namespaced_job(namespace=NAMESPACE, body=job)
        logger.info(f"Created job {job_name} for session {session_id}")
        return job_name
    except Exception as e:
        logger.error(f"Failed to create job: {str(e)}")
        raise


def get_job_status(job_name: str) -> str:
    """Get the status of a Kubernetes job"""
    try:
        job = batch_v1.read_namespaced_job(name=job_name, namespace=NAMESPACE)

        if job.status.succeeded:
            return "Completed"
        elif job.status.failed:
            return "Failed"
        elif job.status.active:
            return "Running"
        else:
            return "Pending"
    except Exception as e:
        logger.error(f"Failed to get job status: {str(e)}")
        return "Unknown"


def get_pod_logs(session_id: str) -> str:
    """Get logs from the pod associated with the session"""
    try:
        # Find pods with the session-id label
        pods = core_v1.list_namespaced_pod(
            namespace=NAMESPACE, label_selector=f"session-id={session_id}"
        )

        if not pods.items:
            return "No pods found for this session"

        # Get logs from the first pod
        pod_name = pods.items[0].metadata.name
        logs = core_v1.read_namespaced_pod_log(
            name=pod_name, namespace=NAMESPACE, tail_lines=100
        )

        return logs
    except Exception as e:
        logger.error(f"Failed to get pod logs: {str(e)}")
        return f"Error fetching logs: {str(e)}"


def get_pod_logs_with_path(session_id: str) -> tuple:
    """Get logs from pod and extract log file path and content if available"""
    try:
        pods = core_v1.list_namespaced_pod(
            namespace=NAMESPACE, label_selector=f"session-id={session_id}"
        )

        if not pods.items:
            return "", None, None

        pod_name = pods.items[0].metadata.name

        # Get main pod logs
        logs = core_v1.read_namespaced_pod_log(
            name=pod_name, namespace=NAMESPACE, tail_lines=200
        )

        log_path = None
        log_content = None

        # Try to extract log file path and content
        try:
            # Read signal file with path
            signal_logs = core_v1.read_namespaced_pod_log(
                name=pod_name, namespace=NAMESPACE
            )

            if "LOG_FILE_PATH:" in signal_logs:
                for line in signal_logs.split("\n"):
                    if "LOG_FILE_PATH:" in line:
                        log_path = line.replace("LOG_FILE_PATH:", "").strip()
                        break
        except:
            pass

        # Try to read the actual log file content
        try:
            log_content = core_v1.read_namespaced_pod_log(
                name=pod_name, namespace=NAMESPACE, container="cai-chat"
            )

            # Look for /tmp/job_logs_content (from the script)
            # We'll try to exec into the pod to read files
            if log_path:
                from kubernetes import stream

                try:
                    exec_command = [
                        "/bin/sh",
                        "-c",
                        f"cat {log_path} 2>/dev/null || echo 'File not accessible'",
                    ]
                    log_content = stream(
                        core_v1.connect_get_namespaced_pod_exec,
                        pod_name,
                        NAMESPACE,
                        command=exec_command,
                        stderr=True,
                        stdin=False,
                        stdout=True,
                        tty=False,
                    )
                except:
                    pass
        except:
            pass

        return logs, log_path, log_content
    except Exception as e:
        logger.error(f"Failed to get pod logs: {str(e)}")
        return f"Error fetching logs: {str(e)}", None, None


@app.post("/api/sessions", response_model=Session)
async def create_session(
    session_data: SessionCreate, background_tasks: BackgroundTasks
):
    """Create a new chat session and start a Kubernetes job"""

    session_id = str(uuid.uuid4())

    try:
        job_name = create_k8s_job(
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


@app.get("/api/sessions", response_model=List[Session])
async def list_sessions():
    """List all chat sessions"""

    # Update session statuses
    for session_id, session in sessions_store.items():
        session["status"] = get_job_status(session["jobName"])

    return list(sessions_store.values())


@app.get("/api/sessions/{session_id}", response_model=Session)
async def get_session(session_id: str):
    """Get a specific session"""

    if session_id not in sessions_store:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions_store[session_id]
    session["status"] = get_job_status(session["jobName"])

    return session


@app.get("/api/sessions/{session_id}/logs", response_model=JobLogs)
async def get_session_logs(session_id: str):
    """Get logs for a specific session and trigger webhook on completion"""

    if session_id not in sessions_store:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions_store[session_id]
    status = get_job_status(session["jobName"])
    logs, log_path, log_content = get_pod_logs_with_path(session_id)

    # Send webhook if job completed and not yet notified
    if status == "Completed" and not session.get("webhook_sent"):
        send_webhook(
            session_id, session["jobName"], status, log_path, logs, log_content
        )
        sessions_store[session_id]["webhook_sent"] = True

    return {"logs": logs, "status": status}


@app.get("/api/sessions/{session_id}/result", response_model=JobResult)
async def get_session_result(session_id: str):
    """Get complete job result including file content"""

    if session_id not in sessions_store:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions_store[session_id]
    status = get_job_status(session["jobName"])

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
    logs, log_path, log_content = get_pod_logs_with_path(session_id)

    return {
        "session_id": session_id,
        "status": status,
        "log_path": log_path,
        "pod_logs": logs,
        "file_content": log_content,
        "file_size": len(log_content) if log_content else 0,
    }


@app.get("/api/sessions/{session_id}/file")
async def get_session_file(session_id: str, format: str = "json"):
    """Get the output file content from completed job"""

    if session_id not in sessions_store:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions_store[session_id]
    status = get_job_status(session["jobName"])

    if status != "Completed":
        raise HTTPException(
            status_code=400, detail=f"Job not completed yet. Status: {status}"
        )

    # Try to get from stored result first
    if "result" in session and session["result"].get("file_content"):
        file_content = session["result"]["file_content"]
    else:
        # Fetch fresh logs
        logs, log_path, file_content = get_pod_logs_with_path(session_id)

    if not file_content:
        raise HTTPException(status_code=404, detail="No output file found")

    if format == "raw":
        from fastapi.responses import PlainTextResponse

        return PlainTextResponse(content=file_content)

    # Return as JSON (parse if it's JSONL)
    try:
        lines = [
            json.loads(line)
            for line in file_content.strip().split("\n")
            if line.strip()
        ]
        return {"data": lines, "count": len(lines)}
    except:
        return {"data": file_content, "format": "text"}


@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    """Delete a session and its associated Kubernetes job"""

    if session_id not in sessions_store:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions_store[session_id]
    job_name = session["jobName"]

    try:
        # Delete the job
        batch_v1.delete_namespaced_job(
            name=job_name, namespace=NAMESPACE, propagation_policy="Background"
        )

        # Remove from store
        del sessions_store[session_id]

        return {"message": "Session deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to delete session: {str(e)}"
        )


@app.post("/api/webhooks")
async def receive_webhook(payload: dict):
    """Receive webhook notifications from completed jobs"""
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


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


async def monitor_jobs():
    """Background task to monitor job completions and send webhooks"""
    while True:
        try:
            await asyncio.sleep(10)  # Check every 10 seconds

            for session_id, session in list(sessions_store.items()):
                if session.get("webhook_sent"):
                    continue

                status = get_job_status(session["jobName"])
                session["status"] = status

                # Send webhook when job completes
                if status in ["Completed", "Failed"]:
                    logger.info(
                        f"Job {session['jobName']} completed with status: {status}"
                    )
                    logs, log_path, log_content = get_pod_logs_with_path(session_id)
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


@app.on_event("startup")
async def startup_event():
    """Startup event handler"""
    logger.info("CAI Kubernetes Job Manager started")

    # Sync existing jobs on startup
    try:
        jobs = batch_v1.list_namespaced_job(namespace=NAMESPACE)
        for job in jobs.items:
            if "session-id" in job.metadata.labels:
                session_id = job.metadata.labels["session-id"]
                if session_id not in sessions_store:
                    sessions_store[session_id] = {
                        "id": session_id,
                        "name": job.metadata.labels.get("session-name", "Unknown"),
                        "status": get_job_status(job.metadata.name),
                        "created": job.metadata.creation_timestamp.isoformat(),
                        "jobName": job.metadata.name,
                        "prompt": "Recovered from existing job",
                    }
        logger.info(f"Synced {len(sessions_store)} existing sessions")
    except Exception as e:
        logger.error(f"Failed to sync existing jobs: {str(e)}")

    # Start background job monitor
    asyncio.create_task(monitor_jobs())
    logger.info("Background job monitor started")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

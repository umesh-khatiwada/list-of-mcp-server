from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from kubernetes import client, config
from typing import Optional, List
import uuid
import logging
from datetime import datetime
import asyncio
import os

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

# Kubernetes configuration
NAMESPACE = "default"  # Change to your namespace
CAI_IMAGE = "docker.io/neptune1212/cai:arm64"

def sanitize_label(value: str) -> str:
    """Sanitize a string to be used as a Kubernetes label"""
    # Replace spaces and invalid chars with hyphens
    sanitized = value.replace(" ", "-").replace("_", "-")
    # Remove any character that's not alphanumeric, hyphen, or dot
    sanitized = ''.join(c for c in sanitized if c.isalnum() or c in ['-', '.'])
    # Ensure it starts and ends with alphanumeric
    sanitized = sanitized.strip('-.')
    # Limit to 63 characters (K8s label limit)
    return sanitized[:63]

def create_k8s_job(session_id: str, session_name: str, prompt: str, 
                   character_id: Optional[str] = None, token: Optional[str] = None):
    """Create a Kubernetes Job for CAI chat session"""
    
    job_name = f"cai-job-{session_id[:8]}"
    sanitized_name = sanitize_label(session_name)
    
    # Environment variables for the CAI container
    env_vars = [
        client.V1EnvVar(name="PROMPT", value=prompt),
        client.V1EnvVar(name="SESSION_ID", value=session_id),
        client.V1EnvVar(name="DEEPSEEK_API_KEY", value=os.getenv("DEEPSEEK_API_KEY", "")),
        client.V1EnvVar(name="CAI_MODEL", value="deepseek-chat"),
        client.V1EnvVar(name="OPENAI_API_KEY", value=os.getenv("OPENAI_API_KEY", "")),
        client.V1EnvVar(name="CAI_STEAM", value=os.getenv("CAI_STEAM", "true")),
        client.V1EnvVar(name="CAI_AGENT_TYPE", value=os.getenv("CAI_AGENT_TYPE", "offsec_pattern")),
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
        command=["/bin/bash"],
        args=[
            "-c",
            f"""
            source /cai/bin/activate
            cat << 'EOF' > /tmp/cai_commands.txt
/agent offsec_pattern
{prompt}
EOF
            
            # Execute CAI with piped commands
            cat /tmp/cai_commands.txt | cai
            """
        ]
    )
    
    # Define the pod template
    template = client.V1PodTemplateSpec(
        metadata=client.V1ObjectMeta(
            labels={
                "app": "cai-chat",
                "session-id": session_id
            }
        ),
        spec=client.V1PodSpec(
            restart_policy="Never",
            containers=[container]
        )
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
                "app": "cai-chat"
            }
        ),
        spec=client.V1JobSpec(
            template=template,
            backoff_limit=3,
            ttl_seconds_after_finished=3600  # Clean up after 1 hour
        )
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
            namespace=NAMESPACE,
            label_selector=f"session-id={session_id}"
        )
        
        if not pods.items:
            return "No pods found for this session"
        
        # Get logs from the first pod
        pod_name = pods.items[0].metadata.name
        logs = core_v1.read_namespaced_pod_log(
            name=pod_name,
            namespace=NAMESPACE,
            tail_lines=100
        )
        
        return logs
    except Exception as e:
        logger.error(f"Failed to get pod logs: {str(e)}")
        return f"Error fetching logs: {str(e)}"

@app.post("/api/sessions", response_model=Session)
async def create_session(session_data: SessionCreate, background_tasks: BackgroundTasks):
    """Create a new chat session and start a Kubernetes job"""
    
    session_id = str(uuid.uuid4())
    
    try:
        job_name = create_k8s_job(
            session_id=session_id,
            session_name=session_data.name,
            prompt=session_data.prompt,
            character_id=session_data.character_id,
            token=session_data.token
        )
        
        session = {
            "id": session_id,
            "name": session_data.name,
            "status": "Pending",
            "created": datetime.now().isoformat(),
            "jobName": job_name,
            "prompt": session_data.prompt
        }
        
        sessions_store[session_id] = session
        
        return session
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")

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
    """Get logs for a specific session"""
    
    if session_id not in sessions_store:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session = sessions_store[session_id]
    logs = get_pod_logs(session_id)
    status = get_job_status(session["jobName"])
    
    return {"logs": logs, "status": status}

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
            name=job_name,
            namespace=NAMESPACE,
            propagation_policy="Background"
        )
        
        # Remove from store
        del sessions_store[session_id]
        
        return {"message": "Session deleted successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

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
                        "prompt": "Recovered from existing job"
                    }
        logger.info(f"Synced {len(sessions_store)} existing sessions")
    except Exception as e:
        logger.error(f"Failed to sync existing jobs: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
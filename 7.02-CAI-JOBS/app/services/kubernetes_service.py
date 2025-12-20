"""Kubernetes service for managing jobs and pods."""
import logging
from typing import Optional, Tuple

from kubernetes import client, config

from ..config import settings
from ..utils import sanitize_label

logger = logging.getLogger(__name__)

# Load Kubernetes config
try:
    config.load_incluster_config()  # Use this when running in cluster
except Exception:
    config.load_kube_config()  # Use this for local development

# Kubernetes clients
batch_v1 = client.BatchV1Api()
core_v1 = client.CoreV1Api()


class KubernetesService:
    """Service for managing Kubernetes jobs and pods."""

    def __init__(self):
        """Initialize the Kubernetes service."""
        self.batch_v1 = batch_v1
        self.core_v1 = core_v1
        self.namespace = settings.namespace

    def create_job(
        self,
        session_id: str,
        session_name: str,
        prompt: str,
        character_id: Optional[str] = None,
        token: Optional[str] = None,
    ) -> str:
        """Create a Kubernetes Job for CAI chat session.

        Args:
            session_id: Unique session identifier
            session_name: Human readable session name
            prompt: The prompt to process
            character_id: Optional character ID
            token: Optional authentication token

        Returns:
            The created job name

        Raises:
            Exception: If job creation fails
        """
        job_name = f"cai-job-{session_id[:8]}"
        sanitized_name = sanitize_label(session_name)

        # Environment variables for the CAI container
        env_vars = [
            client.V1EnvVar(name="PROMPT", value=prompt),
            client.V1EnvVar(name="SESSION_ID", value=session_id),
            client.V1EnvVar(name="DEEPSEEK_API_KEY", value=settings.deepseek_api_key),
            client.V1EnvVar(name="CAI_MODEL", value=settings.cai_model),
            client.V1EnvVar(name="OPENAI_API_KEY", value=settings.openai_api_key),
            client.V1EnvVar(name="CAI_STREAM", value=settings.cai_stream),
            client.V1EnvVar(name="CAI_AGENT_TYPE", value=settings.cai_agent_type),
            client.V1EnvVar(name="CAI_DEBUG", value="0"),
            client.V1EnvVar(name="CAI_BRIEF", value="true"),
        ]

        if character_id:
            env_vars.append(client.V1EnvVar(name="CHARACTER_ID", value=character_id))
        if token:
            env_vars.append(client.V1EnvVar(name="CAI_TOKEN", value=token))

        # Define the container
        container = client.V1Container(
            name="cai-chat",
            image=settings.cai_image,
            env=env_vars,
            image_pull_policy="Always",
            command=["/bin/bash", "-c"],
            args=[
                f"""#!/bin/bash
set -e

# Activate CAI environment
source /home/kali/cai/bin/activate

# Set environment variables for non-interactive mode
export CAI_MODEL={settings.cai_model}
export CAI_AGENT_TYPE={settings.cai_agent_type}
export CAI_STREAM=false
export CAI_DEBUG=1
export CAI_BRIEF=true
export CAI_MAX_TURNS=50
export CAI_PRICE_LIMIT=10.0
export CAI_INTERACTIVE=false
export TERM=dumb

# Log environment for debugging
echo "=== CAI Environment ==="
echo "CAI_MODEL: $CAI_MODEL"
echo "CAI_AGENT_TYPE: $CAI_AGENT_TYPE"
echo "CAI_STREAM: $CAI_STREAM"
echo "CAI_DEBUG: $CAI_DEBUG"
echo "PROMPT: {prompt}"
echo "======================="

# Try multiple approaches to run CAI non-interactively

# Approach 1: Use --prompt flag directly
echo "Attempting method 1: --prompt flag"
timeout 300 cai --agent {settings.cai_agent_type} --model {settings.cai_model} --prompt "{prompt}" --non-interactive 2>&1 || echo "Method 1 failed"

# Approach 2: Use echo and pipe
echo "Attempting method 2: echo pipe"
echo "{prompt}" | timeout 300 cai --agent {settings.cai_agent_type} --model {settings.cai_model} 2>&1 || echo "Method 2 failed"

# Approach 3: Use here document
echo "Attempting method 3: here document"
timeout 300 cai --agent {settings.cai_agent_type} --model {settings.cai_model} << 'PROMPT_EOF' 2>&1 || echo "Method 3 failed"
{prompt}
/exit
PROMPT_EOF

# Approach 4: Create script file and use it
echo "Attempting method 4: script file"
cat > /tmp/cai_script.txt << 'SCRIPT_EOF'
/agent {settings.cai_agent_type}
/model {settings.cai_model}
{prompt}
/save /tmp/cai_results.json
/exit
SCRIPT_EOF

timeout 300 cai < /tmp/cai_script.txt 2>&1 || echo "Method 4 failed"

echo "All methods attempted"

# Capture logs and results
EXIT_CODE=0
echo "Looking for log files..."

# Find and process log files
if [ -d /home/kali/logs ]; then
  echo "Found logs directory"
  ls -la /home/kali/logs/
  LOGFILE=$(find /home/kali/logs -name "cai_*.jsonl" -type f 2>/dev/null | head -1)
  if [ -n "$LOGFILE" ] && [ -f "$LOGFILE" ]; then
    echo "LOG_FILE_PATH: $LOGFILE"
    echo "$LOGFILE" > /tmp/job_completion_signal
    cat "$LOGFILE" > /tmp/job_logs_content
    echo "Log file captured: $(wc -l < "$LOGFILE") lines"
  else
    echo "No JSONL log file found"
  fi
else
  echo "No logs directory found"
fi

# Check for results file
if [ -f /tmp/cai_results.json ]; then
  echo "Results file found"
  cat /tmp/cai_results.json > /tmp/job_results_content
fi

exit $EXIT_CODE
    echo "LOG_FILE_PATH: $LOGFILE"
    echo "$LOGFILE" > /tmp/job_completion_signal
    cat "$LOGFILE" > /tmp/job_logs_content
  fi
fi

# Copy results if available
if [ -f /tmp/cai_results.json ]; then
  cat /tmp/cai_results.json > /tmp/job_results_content
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
                        config_map=client.V1ConfigMapVolumeSource(
                            name="cai-agents-config"
                        ),
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
            self.batch_v1.create_namespaced_job(namespace=self.namespace, body=job)
            logger.info(f"Created job {job_name} for session {session_id}")
            return job_name
        except Exception as e:
            logger.error(f"Failed to create job: {str(e)}")
            raise

    def get_job_status(self, job_name: str) -> str:
        """Get the status of a Kubernetes job.

        Args:
            job_name: The name of the job

        Returns:
            The job status string
        """
        try:
            job = self.batch_v1.read_namespaced_job(
                name=job_name, namespace=self.namespace
            )

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

    def get_pod_logs(self, session_id: str) -> str:
        """Get logs from the pod associated with the session.

        Args:
            session_id: The session ID

        Returns:
            The pod logs as a string
        """
        try:
            # Find pods with the session-id label
            pods = self.core_v1.list_namespaced_pod(
                namespace=self.namespace, label_selector=f"session-id={session_id}"
            )

            if not pods.items:
                return "No pods found for this session"

            # Get logs from the first pod
            pod_name = pods.items[0].metadata.name
            logs = self.core_v1.read_namespaced_pod_log(
                name=pod_name, namespace=self.namespace, tail_lines=100
            )

            return logs
        except Exception as e:
            logger.error(f"Failed to get pod logs: {str(e)}")
            return f"Error fetching logs: {str(e)}"

    def get_pod_logs_with_path(
        self, session_id: str
    ) -> Tuple[str, Optional[str], Optional[str]]:
        """Get logs from pod and extract log file path and content if available.

        Args:
            session_id: The session ID

        Returns:
            Tuple of (pod_logs, log_path, log_content)
        """
        try:
            pods = self.core_v1.list_namespaced_pod(
                namespace=self.namespace, label_selector=f"session-id={session_id}"
            )

            if not pods.items:
                return "", None, None

            pod_name = pods.items[0].metadata.name

            # Get main pod logs
            logs = self.core_v1.read_namespaced_pod_log(
                name=pod_name, namespace=self.namespace, tail_lines=200
            )

            log_path = None
            log_content = None

            # Try to extract log file path and content
            try:
                # Read signal file with path
                signal_logs = self.core_v1.read_namespaced_pod_log(
                    name=pod_name, namespace=self.namespace
                )

                if "LOG_FILE_PATH:" in signal_logs:
                    for line in signal_logs.split("\n"):
                        if "LOG_FILE_PATH:" in line:
                            log_path = line.replace("LOG_FILE_PATH:", "").strip()
                            break
            except Exception:
                pass

            # Try to read the actual log file content
            try:
                log_content = self.core_v1.read_namespaced_pod_log(
                    name=pod_name, namespace=self.namespace, container="cai-chat"
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
                            self.core_v1.connect_get_namespaced_pod_exec,
                            pod_name,
                            self.namespace,
                            command=exec_command,
                            stderr=True,
                            stdin=False,
                            stdout=True,
                            tty=False,
                        )
                    except Exception:
                        pass
            except Exception:
                pass

            return logs, log_path, log_content
        except Exception as e:
            logger.error(f"Failed to get pod logs: {str(e)}")
            return f"Error fetching logs: {str(e)}", None, None

    def delete_job(self, job_name: str) -> None:
        """Delete a Kubernetes job.

        Args:
            job_name: The name of the job to delete

        Raises:
            Exception: If job deletion fails
        """
        try:
            self.batch_v1.delete_namespaced_job(
                name=job_name, namespace=self.namespace, propagation_policy="Background"
            )
            logger.info(f"Deleted job {job_name}")
        except Exception as e:
            logger.error(f"Failed to delete job {job_name}: {str(e)}")
            raise

    def list_jobs(self) -> list:
        """List all jobs in the namespace.

        Returns:
            List of job objects
        """
        try:
            jobs = self.batch_v1.list_namespaced_job(namespace=self.namespace)
            return jobs.items
        except Exception as e:
            logger.error(f"Failed to list jobs: {str(e)}")
            return []

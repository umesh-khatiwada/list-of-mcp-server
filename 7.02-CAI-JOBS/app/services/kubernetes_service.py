"""Kubernetes service for managing jobs and pods."""
import logging
from typing import List, Optional, Tuple

from kubernetes import client, config

from ..config import settings
from ..models.mcp import MCPServerConfig, MCPTransport
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

    def _render_mcp_load_commands(
        self,
        mcp_servers: Optional[List[MCPServerConfig]],
        agent_type: Optional[str] = None,
    ) -> str:
        """Render /mcp load commands for CAI.

        Args:
            mcp_servers: Optional list of MCP server configs

        Returns:
            String containing MCP load commands or a comment placeholder
        """

        if not mcp_servers:
            return "/mcp list"

        commands: List[str] = ["/mcp list"]
        target_agent = agent_type or settings.cai_agent_type

        for server in mcp_servers:
            if server.transport == MCPTransport.SSE:
                commands.append(f"/mcp load {server.url} {server.name}")
            else:
                commands.append(f"/mcp load stdio {server.name} {server.command}")

            # Bind the MCP to the agent group so CAI can route properly
            if target_agent:
                commands.append(f"/mcp add {server.name} {target_agent}")

        return "\n".join(commands)

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
        mcp_servers: Optional[List[MCPServerConfig]] = None,
        workspace_path: Optional[str] = None,
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
            client.V1EnvVar(name="LITELLM_DISABLE_AUTH", value="true"),
            # Critical: Set non-interactive mode
            client.V1EnvVar(name="CAI_INTERACTIVE", value="false"),
            client.V1EnvVar(name="TERM", value="dumb"),
        ]

        if character_id:
            env_vars.append(client.V1EnvVar(name="CHARACTER_ID", value=character_id))
        if token:
            env_vars.append(client.V1EnvVar(name="CAI_TOKEN", value=token))
        if workspace_path:
            env_vars.append(
                client.V1EnvVar(name="REQUESTED_WORKSPACE", value=workspace_path)
            )

        mcp_block = self._render_mcp_load_commands(
            mcp_servers, agent_type=settings.cai_agent_type
        )

        workspace_cd_block = ""
        workspace_command_block = ""

        if workspace_path:
            workspace_cd_block = f"""
# Switch to requested workspace if present
if [ -d "{workspace_path}" ]; then
  cd "{workspace_path}"
  echo "Changed directory to {workspace_path}"
else
  echo "Requested workspace {workspace_path} not found; staying in $(pwd)"
fi
"""
            workspace_command_block = f"/workspace set {workspace_path}"

        prompt_payload = prompt.replace("{{session_id}}", session_id).replace(
            "{{SESSION_ID}}", session_id
        )
        if workspace_path:
            prompt_payload = prompt_payload.replace(
                "{{workspace_path}}", workspace_path
            ).replace("{{WORKSPACE_PATH}}", workspace_path)

        prelude_parts: List[str] = []
        if mcp_block and mcp_block.strip():
            prelude_parts.append(mcp_block.strip())
        if workspace_command_block:
            prelude_parts.append(workspace_command_block)

        prelude_content = (
            "\n\n".join(part for part in prelude_parts if part.strip())
            if prelude_parts
            else "# No CAI setup commands"
        )
        workspace_cd_script = (
            f"{workspace_cd_block.strip()}\n" if workspace_cd_block else ""
        )

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
export CAI_DEBUG=0
export CAI_BRIEF=true
export CAI_MAX_TURNS=50
export CAI_PRICE_LIMIT=10.0
export CAI_INTERACTIVE=false
export TERM=dumb
export PYTHONUNBUFFERED=1

# Redirect stdin to avoid terminal issues
exec 0</dev/null

echo "Starting CAI chat job for session $SESSION_ID"

{workspace_cd_script}# Prepare CAI payload segments
cat > /tmp/cai_prelude.txt << 'PRELUDE_EOF'
{prelude_content}
PRELUDE_EOF

cat > /tmp/cai_prompt.txt << 'PROMPT_EOF'
{prompt}
PROMPT_EOF

cat > /tmp/cai_footer.txt << 'FOOTER_EOF'
/save /tmp/cai_results.json
/quit
FOOTER_EOF

# Combine all parts into final payload
cat /tmp/cai_prelude.txt /tmp/cai_prompt.txt /tmp/cai_footer.txt > /tmp/cai_payload.txt

# Copy agents config
cp /config/agents.yml . 2>/dev/null || echo "No agents.yml config found"

# Execute CAI with the prepared payload in non-interactive mode
echo "Starting CAI run"
echo "-----------------------------------"
echo "/tmp/cai_payload.txt contents:    "
cat /tmp/cai_payload.txt
EXIT_CODE=0

# Method 1: Try using CAI with stdin redirect (primary method)
if ! cat /tmp/cai_payload.txt | cai 2>&1; then
    EXIT_CODE=$?
    echo "CAI execution failed with exit code $EXIT_CODE"

    # Method 2: Fallback - try with explicit flags if available
    if command -v cai-noninteractive >/dev/null 2>&1; then
        echo "Attempting fallback with cai-noninteractive"
        EXIT_CODE=0
        if ! cat /tmp/cai_payload.txt | cai-noninteractive 2>&1; then
            EXIT_CODE=$?
        fi
    fi
fi

echo "CAI execution complete"

# Capture logs and results
echo "Looking for log files..."

# Find and process log files
if [ -d /home/kali/logs ]; then
    echo "Found logs directory"
    ls -la /home/kali/logs/ || true
    LOGFILE=$(find /home/kali/logs -name "cai_*.jsonl" -type f 2>/dev/null | head -1)
    if [ -n "$LOGFILE" ] && [ -f "$LOGFILE" ]; then
        echo "LOG_FILE_PATH: $LOGFILE"
        echo "$LOGFILE" > /tmp/job_completion_signal
        cat "$LOGFILE" > /tmp/job_logs_content
        LINE_COUNT=$(wc -l < "$LOGFILE" 2>/dev/null || echo "0")
        echo "Log file captured: ${{LINE_COUNT}} lines"
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
    echo "Results content captured"
else
    echo "No results file found at /tmp/cai_results.json"
fi

# Always exit with success unless CAI critically failed
if [ $EXIT_CODE -eq 0 ] || [ -f /tmp/job_logs_content ]; then
    echo "Job completed successfully"
    exit 0
else
    echo "Job failed with exit code $EXIT_CODE"
    exit $EXIT_CODE
fi
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
        except client.ApiException as e:
            if e.status == 404:
                logger.info(f"Job {job_name} not found (deleted or expired)")
                return "Deleted"
            logger.error(f"Failed to get job status: {str(e)}")
            return "Unknown"
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
                        log_content = stream.stream(
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

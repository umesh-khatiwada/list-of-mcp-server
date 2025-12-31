"""Kubernetes service for managing jobs and pods."""
import logging
from typing import List, Optional, Tuple

from kubernetes import client, config
import requests
import time
from datetime import datetime
import yaml

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
                # No pod found locally; if Loki configured try to fetch by job/session label
                if settings.loki_url:
                    try:
                        # Query Loki trying several common label keys to discover streams
                        now_ns = int(time.time() * 1e9)
                        start_ns = now_ns - int(3600 * 1e9)  # last 1 hour
                        loki_endpoint = f"{settings.loki_url.rstrip('/')}/loki/api/v1/query_range"
                        session_id_short = session_id[:8]

                        # Candidate label keys and templates to try - improved matching
                        label_candidates = [
                            ('session-id_exact', f'{{session_id="{session_id}"}}'),
                            ('session-id_alt', f'{{session-id="{session_id}"}}'),
                            ('pod_session_regex', f'{{pod=~".*{session_id_short}.*"}}'),
                            ('job_name_session_regex', f'{{job_name=~".*{session_id_short}.*"}}'),
                            ('job_session_regex', f'{{job=~".*{session_id_short}.*"}}'),
                            ('namespace_app', f'{{namespace="{self.namespace}",app="cai-chat"}}'),
                            ('namespace_only', f'{{namespace="{self.namespace}"}}'),
                        ]

                        for label_name, q in label_candidates:
                            try:
                                params = {
                                    "query": q,
                                    "limit": 500,
                                    "direction": "backward",
                                    "start": start_ns,
                                    "end": now_ns,
                                }
                                logger.info(f"Querying Loki at {loki_endpoint} for session {session_id} trying label {label_name} query={q}")
                                res = requests.get(loki_endpoint, params=params, timeout=15)
                                logger.info(f"Loki response for label {label_name}: status={res.status_code}")
                                if not res.ok:
                                    logger.debug(f"Loki query failed with status {res.status_code}")
                                    continue
                                data = res.json().get("data", {})
                                result_streams = data.get("result", [])
                                
                                if not result_streams:
                                    continue
                                
                                logs = []
                                for stream in result_streams:
                                    for v in stream.get("values", []):
                                        logs.append(v[1])
                                
                                if not logs:
                                    # no entries for this label, try next
                                    continue

                                logs_str = "\n".join(reversed(logs))
                                log_path = None
                                for line in logs_str.split('\n'):
                                    if 'LOG_FILE_PATH:' in line:
                                        log_path = line.replace('LOG_FILE_PATH:', '').strip()
                                        break

                                # Prefix logs with source info so UI can show where they came from
                                prefixed = f"SOURCE: LOKI (label={label_name})\n" + logs_str
                                logger.info(f"Successfully retrieved {len(logs)} log lines from Loki using label {label_name}")
                                return prefixed, log_path, None
                            except requests.exceptions.RequestException as le_inner:
                                logger.warning(f"Loki request failed for label {label_name}: {le_inner}")
                                continue
                            except Exception as le_inner:
                                logger.warning(f"Loki attempt for label {label_name} failed: {le_inner}")
                                continue
                    except Exception as le:
                        logger.warning(f"Loki query failed: {str(le)}")
                return "", None, None

            pod = pods.items[0]
            pod_name = pod.metadata.name

            # If Loki is configured, prefer Loki for aggregated logs
            if settings.loki_url:
                try:
                    now_ns = int(time.time() * 1e9)
                    start_ns = now_ns - int(3600 * 1e9)  # last 1 hour

                    # Get labels from pod metadata
                    job_label = None
                    if pod.metadata.labels:
                        job_label = pod.metadata.labels.get("job-name") or pod.metadata.labels.get("job_name")

                    # Build label candidates - prioritize exact matches
                    label_candidates = []
                    
                    # Most specific: exact pod name
                    label_candidates.append(('pod_exact', f'{{pod="{pod_name}"}}'))
                    
                    # Job name from pod labels (Kubernetes standard)
                    if job_label:
                        label_candidates.append(('job_name_exact', f'{{job_name="{job_label}"}}'))
                    
                    # Session ID based
                    session_id_short = session_id[:8]
                    label_candidates.append(('session_id', f'{{session_id="{session_id}"}}'))
                    label_candidates.append(('session_id_alt', f'{{session-id="{session_id}"}}'))
                    
                    # Namespace + app combination
                    label_candidates.append(('namespace_app', f'{{namespace="{self.namespace}",app="cai-chat"}}'))

                    loki_endpoint = f"{settings.loki_url.rstrip('/')}/loki/api/v1/query_range"
                    
                    # Try each label candidate
                    for label_name, q in label_candidates:
                        try:
                            params = {
                                "query": q,
                                "limit": 500,
                                "direction": "backward",
                                "start": start_ns,
                                "end": now_ns,
                            }
                            logger.info(f"Querying Loki at {loki_endpoint} for pod {pod_name} (job: {job_label}) trying label {label_name} query={q}")
                            res = requests.get(loki_endpoint, params=params, timeout=15)
                            logger.info(f"Loki response for label {label_name}: status={res.status_code}")
                            
                            if not res.ok:
                                logger.debug(f"Loki query failed with status {res.status_code}")
                                continue
                            
                            data = res.json().get("data", {})
                            result_streams = data.get("result", [])
                            
                            if not result_streams:
                                logger.debug(f"No streams found for label {label_name}")
                                continue
                            
                            logs = []
                            for stream in result_streams:
                                for v in stream.get("values", []):
                                    logs.append(v[1])

                            if not logs:
                                logger.debug(f"No log entries found for label {label_name}")
                                continue

                            logs_str = "\n".join(reversed(logs))
                            logger.info(f"Successfully retrieved {len(logs)} log lines from Loki using label {label_name}")

                            log_path = None
                            for line in logs_str.split('\n'):
                                if 'LOG_FILE_PATH:' in line:
                                    log_path = line.replace('LOG_FILE_PATH:', '').strip()
                                    break

                            # If we found a file path and pod is present, try exec to get full file content
                            log_content = None
                            if log_path:
                                try:
                                    from kubernetes import stream

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
                                except Exception as e:
                                    logger.info(f"Failed to exec into pod to fetch file {log_path}: {e}")
                                    log_content = None

                            return logs_str, log_path, log_content
                            
                        except requests.exceptions.RequestException as e:
                            logger.warning(f"Loki request failed for label {label_name}: {e}")
                            continue
                        except Exception as e:
                            logger.warning(f"Loki query exception for label {label_name}: {str(e)}")
                            continue
                    
                    logger.info("All Loki label queries failed, falling back to Kubernetes logs")
                except Exception as e:
                    logger.warning(f"Loki query exception: {str(e)}")

            # Fallback to direct Kubernetes pod logs
            logs = self.core_v1.read_namespaced_pod_log(
                name=pod_name, namespace=self.namespace, tail_lines=200
            )

            log_path = None
            log_content = None

            # Try to extract log file path and content from pod logs
            try:
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

            # Try to read the actual log file content via exec into pod
            try:
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

    def get_manifestwork_status(self, manifestwork_name: str) -> str:
        """Get the status of a ManifestWork.

        Args:
            manifestwork_name: The name of the ManifestWork

        Returns:
            The ManifestWork status string
        """
        try:
            from kubernetes.client import CustomObjectsApi
            custom_api = CustomObjectsApi()
            
            logger.info(f"Getting ManifestWork {manifestwork_name} in namespace {settings.managed_cluster_namespace}")
            manifestwork = custom_api.get_namespaced_custom_object(
                group="work.open-cluster-management.io",
                version="v1",
                namespace=settings.managed_cluster_namespace,
                plural="manifestworks",
                name=manifestwork_name
            )
            
            conditions = manifestwork.get('status', {}).get('conditions', [])
            applied = any(c.get('type') == 'Applied' and c.get('status') == 'True' for c in conditions)
            available = any(c.get('type') == 'Available' and c.get('status') == 'True' for c in conditions)
            
            logger.info(f"ManifestWork {manifestwork_name} applied: {applied}, available: {available}")
            if available:
                return "Completed"  # Assume completed when available
            elif applied:
                return "Running"
            else:
                return "Pending"
        except Exception as e:
            # Handle ApiException 404 (not found) as a deleted/expired ManifestWork
            try:
                from kubernetes.client.rest import ApiException
                if isinstance(e, ApiException) and getattr(e, 'status', None) == 404:
                    logger.info(f"ManifestWork {manifestwork_name} not found (deleted or not created)")
                    return "Deleted"
            except Exception:
                pass

            logger.error(f"Failed to get ManifestWork status: {str(e)}")
            return "Unknown"

    def get_manifestwork_logs(self, manifestwork_name: str) -> Tuple[str, Optional[str], Optional[str]]:
        """Get logs for a ManifestWork from Loki.

        Args:
            manifestwork_name: The name of the ManifestWork

        Returns:
            Tuple of (logs, log_path, log_content)
        """
        if not settings.loki_url:
            return "Loki not configured", None, None

        try:
            # Extract session_id_prefix from manifestwork_name
            # For cai-session-abc123 -> abc123
            # For cai-parallel-abc123-0 -> abc123
            parts = manifestwork_name.split('-')
            if len(parts) >= 3 and parts[0] == 'cai':
                session_id_prefix = parts[2]  # abc123
            else:
                session_id_prefix = manifestwork_name

            now_ns = int(time.time() * 1e9)
            start_ns = now_ns - int(3600 * 1e9)  # last 1 hour
            loki_endpoint = f"{settings.loki_url.rstrip('/')}/loki/api/v1/query_range"

            # Try different label queries - improved matching
            label_candidates = [
                ('manifestwork_exact', f'{{manifestwork="{manifestwork_name}"}}'),
                ('job_exact', f'{{job="{manifestwork_name}"}}'),
                ('job_name_exact', f'{{job_name="{manifestwork_name}"}}'),
                ('session_id_regex', f'{{session_id=~"{session_id_prefix}.*"}}'),
                ('session_id_alt_regex', f'{{session-id=~"{session_id_prefix}.*"}}'),
                ('pod_regex', f'{{pod=~".*{session_id_prefix}.*"}}'),
                ('job_name_regex', f'{{job_name=~".*{session_id_prefix}.*"}}'),
            ]

            for label_name, q in label_candidates:
                try:
                    params = {
                        "query": q,
                        "limit": 500,
                        "direction": "backward",
                        "start": start_ns,
                        "end": now_ns,
                    }
                    logger.info(f"Querying Loki for ManifestWork {manifestwork_name} with label {label_name} query={q}")
                    res = requests.get(loki_endpoint, params=params, timeout=15)
                    logger.info(f"Loki response for label {label_name}: status={res.status_code}")
                    
                    if not res.ok:
                        logger.debug(f"Loki query failed with status {res.status_code}")
                        continue
                    
                    data = res.json().get("data", {})
                    result_streams = data.get("result", [])
                    
                    if not result_streams:
                        logger.debug(f"No streams found for label {label_name}")
                        continue
                    
                    logs = []
                    for stream in result_streams:
                        for v in stream.get("values", []):
                            logs.append(v[1])
                    
                    if logs:
                        logs_str = "\n".join(reversed(logs))
                        log_path = None
                        for line in logs_str.split('\n'):
                            if 'LOG_FILE_PATH:' in line:
                                log_path = line.replace('LOG_FILE_PATH:', '').strip()
                                break
                        logger.info(f"Successfully retrieved {len(logs)} log lines from Loki using label {label_name}")
                        return logs_str, log_path, None
                except requests.exceptions.RequestException as e:
                    logger.warning(f"Loki request failed for ManifestWork {manifestwork_name} label {label_name}: {e}")
                    continue
                except Exception as e:
                    logger.warning(f"Loki attempt for ManifestWork {manifestwork_name} with label {label_name} failed: {e}")
                    continue

            return "No logs found in Loki", None, None
        except Exception as e:
            logger.error(f"Failed to get ManifestWork logs: {str(e)}")
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

    def get_manifest(self, job_name: str) -> str:
        """Get the YAML manifest for a job or ManifestWork."""
        try:
            # Assume job first; adjust for ManifestWork if needed
            job = self.batch_v1.read_namespaced_job(name=job_name, namespace=self.namespace)
            return yaml.dump(job.to_dict())
        except Exception as e:
            # Fallback or handle ManifestWork
            try:
                mw = self.custom_api.get_namespaced_custom_object(
                    group="work.open-cluster-management.io",
                    version="v1",
                    namespace=self.namespace,
                    plural="manifestworks",
                    name=job_name
                )
                return yaml.dump(mw)
            except Exception:
                raise ValueError(f"Failed to get manifest for {job_name}: {str(e)}")

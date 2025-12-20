"""Advanced Kubernetes service with CAI integration features."""
import logging
from typing import Dict, List, Optional, Tuple

from kubernetes import client

from ..config import settings
from ..models.advanced import (
    AdvancedSessionCreate,
    QueueItem,
    SessionMode,
)
from ..utils import sanitize_label
from .kubernetes_service import KubernetesService

logger = logging.getLogger(__name__)


class AdvancedKubernetesService(KubernetesService):
    """Advanced Kubernetes service with CAI features."""

    def create_advanced_session(
        self, session_id: str, config: AdvancedSessionCreate
    ) -> Tuple[List[str], SessionMode]:
        """Create an advanced CAI session with multiple execution modes.

        Args:
            session_id: Unique session identifier
            config: Advanced session configuration

        Returns:
            Tuple of (job_names, session_mode)
        """
        # Determine execution mode
        if config.parallel_agents:
            return self._create_parallel_session(session_id, config)
        elif config.queue_items or config.queue_file_content:
            return self._create_queue_session(session_id, config)
        elif config.ctf_config:
            return self._create_ctf_session(session_id, config)
        else:
            # Single agent mode
            job_name = self._create_single_session(session_id, config)
            return [job_name], SessionMode.SINGLE

    def _create_parallel_session(
        self, session_id: str, config: AdvancedSessionCreate
    ) -> Tuple[List[str], SessionMode]:
        """Create parallel execution session."""
        job_names = []

        for i, agent_config in enumerate(config.parallel_agents):
            job_name = f"cai-parallel-{session_id[:8]}-{i}"

            # Build agent-specific command
            agent_command = self._build_cai_command(
                prompt=agent_config.initial_prompt or config.prompt,
                agent_type=agent_config.agent_type,
                model=agent_config.model,
                config=config,
                session_id=f"{session_id}-{i}",
            )

            job = self._create_job_spec(
                job_name=job_name,
                session_id=session_id,
                session_name=config.name,
                command=agent_command,
                config=config,
                agent_alias=agent_config.alias or agent_config.name,
            )

            self.batch_v1.create_namespaced_job(namespace=self.namespace, body=job)
            job_names.append(job_name)
            logger.info(
                f"Created parallel job {job_name} for agent {agent_config.name}"
            )

        return job_names, SessionMode.PARALLEL

    def _create_queue_session(
        self, session_id: str, config: AdvancedSessionCreate
    ) -> Tuple[List[str], SessionMode]:
        """Create queue-based batch processing session."""
        job_name = f"cai-queue-{session_id[:8]}"

        # Build queue commands
        if config.queue_file_content:
            queue_content = config.queue_file_content
        else:
            queue_content = self._build_queue_from_items(config.queue_items)

        # Create queue file in init container
        queue_command = f"""
# Create queue file
cat > /tmp/cai_queue.txt << 'QUEUE_EOF'
{queue_content}
QUEUE_EOF

# Activate environment
source /home/kali/cai/bin/activate

# Set queue file environment variable
export CAI_QUEUE_FILE=/tmp/cai_queue.txt

# Execute CAI with queue
cai --yaml /config/agents.yml

# Capture results
EXIT_CODE=$?
if [ -d /home/kali/logs ]; then
  LOGFILE=$(find /home/kali/logs -name "cai_*.jsonl" -type f 2>/dev/null | head -1)
  if [ -n "$LOGFILE" ]; then
    echo "LOG_FILE_PATH: $LOGFILE"
    cat "$LOGFILE" > /tmp/job_logs_content
  fi
fi
exit $EXIT_CODE
"""

        job = self._create_job_spec(
            job_name=job_name,
            session_id=session_id,
            session_name=config.name,
            command=queue_command,
            config=config,
        )

        self.batch_v1.create_namespaced_job(namespace=self.namespace, body=job)
        logger.info(f"Created queue job {job_name}")

        return [job_name], SessionMode.QUEUE

    def _create_ctf_session(
        self, session_id: str, config: AdvancedSessionCreate
    ) -> Tuple[List[str], SessionMode]:
        """Create CTF-specific session with specialized configuration."""
        job_name = f"cai-ctf-{session_id[:8]}"
        ctf = config.ctf_config

        # CTF-specific environment variables
        ctf_env = {
            "CTF_NAME": ctf.ctf_name,
            "CTF_INSIDE": "true" if ctf.inside_container else "false",
        }

        if ctf.challenge_name:
            ctf_env["CTF_CHALLENGE"] = ctf.challenge_name
        if ctf.subnet:
            ctf_env["CTF_SUBNET"] = ctf.subnet
        if ctf.target_ip:
            ctf_env["CTF_IP"] = ctf.target_ip

        # Build CTF command
        ctf_command = f"""
# Set up CTF environment
export CTF_NAME={ctf.ctf_name}
export CTF_INSIDE=true
{' && '.join(f'export {k}={v}' for k, v in ctf_env.items())}

# Activate environment
source /home/kali/cai/bin/activate

# CTF-specific prompt
cat > /tmp/ctf_prompt.txt << 'CTF_EOF'
{config.prompt or "Analyze and solve the CTF challenge. Find the flag."}
CTF_EOF

# Execute CAI with CTF configuration
cat /tmp/ctf_prompt.txt | cai

# Extract flags and save results
EXIT_CODE=$?
if [ -d /home/kali/logs ]; then
  LOGFILE=$(find /home/kali/logs -name "cai_*.jsonl" -type f 2>/dev/null | head -1)
  if [ -n "$LOGFILE" ]; then
    echo "LOG_FILE_PATH: $LOGFILE"
    # Extract flags
    grep -i "flag{{" "$LOGFILE" > /tmp/flags_found.txt || true
    cat "$LOGFILE" > /tmp/job_logs_content
  fi
fi
exit $EXIT_CODE
"""

        job = self._create_job_spec(
            job_name=job_name,
            session_id=session_id,
            session_name=config.name,
            command=ctf_command,
            config=config,
            additional_env=ctf_env,
        )

        self.batch_v1.create_namespaced_job(namespace=self.namespace, body=job)
        logger.info(f"Created CTF job {job_name} for challenge {ctf.ctf_name}")

        return [job_name], SessionMode.CTF

    def _create_single_session(
        self, session_id: str, config: AdvancedSessionCreate
    ) -> str:
        """Create single agent session."""
        job_name = f"cai-single-{session_id[:8]}"

        command = self._build_cai_command(
            prompt=config.prompt,
            agent_type=config.agent_type,
            model=config.model,
            config=config,
            session_id=session_id,
        )

        job = self._create_job_spec(
            job_name=job_name,
            session_id=session_id,
            session_name=config.name,
            command=command,
            config=config,
        )

        self.batch_v1.create_namespaced_job(namespace=self.namespace, body=job)
        logger.info(f"Created single job {job_name}")

        return job_name

    def _build_cai_command(
        self,
        prompt: str,
        agent_type: str,
        model: str,
        config: AdvancedSessionCreate,
        session_id: str,
    ) -> str:
        """Build CAI command with advanced features."""
        command_parts = [
            "source /home/kali/cai/bin/activate",
            "",
            "# Set up environment variables",
            f"export CAI_MODEL={model}",
            f"export CAI_AGENT_TYPE={agent_type}",
            f"export SESSION_ID={session_id}",
        ]

        # Cost constraints
        cost = config.cost_constraints
        command_parts.extend(
            [
                f"export CAI_PRICE_LIMIT={cost.price_limit}",
                f"export CAI_MAX_TURNS={cost.max_turns or 50}",
            ]
        )

        if cost.max_interactions:
            command_parts.append(f"export CAI_MAX_INTERACTIONS={cost.max_interactions}")

        # Debug and tracing
        if config.debug_level > 0:
            command_parts.append(f"export CAI_DEBUG={config.debug_level}")

        if config.tracing_enabled:
            command_parts.append("export CAI_TRACING=true")

        # Memory configuration
        if config.memory_type.value != "none":
            command_parts.append(f"export CAI_MEMORY={config.memory_type}")
            if config.auto_save_interval:
                command_parts.extend(
                    [
                        "export CAI_MEMORY_ONLINE=true",
                        f"export CAI_MEMORY_ONLINE_INTERVAL={config.auto_save_interval}",
                    ]
                )

        # Workspace configuration
        if config.workspace_path:
            command_parts.append(f"cd {config.workspace_path}")

        # Create prompt file
        command_parts.extend(
            [
                "",
                "# Create prompt file",
                "cat > /tmp/cai_prompt.txt << 'PROMPT_EOF'",
                prompt,
                "PROMPT_EOF",
                "",
            ]
        )

        # Load memory if specified
        if config.load_memory_ids:
            for memory_id in config.load_memory_ids:
                command_parts.append(f"cai --memory apply {memory_id}")

        # Execute main CAI command
        command_parts.extend(
            [
                "# Execute CAI",
                "cat /tmp/cai_prompt.txt | cai --yaml /config/agents.yml",
                "",
                "# Capture results",
                "EXIT_CODE=$?",
                "if [ -d /home/kali/logs ]; then",
                "  LOGFILE=$(find /home/kali/logs -name 'cai_*.jsonl' -type f 2>/dev/null | head -1)",
                '  if [ -n "$LOGFILE" ]; then',
                '    echo "LOG_FILE_PATH: $LOGFILE"',
                '    cat "$LOGFILE" > /tmp/job_logs_content',
                "    # Extract specific patterns",
                "    grep -i 'vulnerability\\|exploit\\|flag{' \"$LOGFILE\" > /tmp/findings.txt || true",
                "  fi",
                "fi",
                "exit $EXIT_CODE",
            ]
        )

        return "\n".join(command_parts)

    def _build_queue_from_items(self, queue_items: List[QueueItem]) -> str:
        """Build queue file content from queue items."""
        lines = ["# Auto-generated queue file"]

        for item in queue_items:
            if item.description:
                lines.append(f"# {item.description}")

            if item.agent_type:
                lines.append(f"/agent {item.agent_type}")

            lines.append(item.command)
            lines.append("")

        return "\n".join(lines)

    def _create_job_spec(
        self,
        job_name: str,
        session_id: str,
        session_name: str,
        command: str,
        config: AdvancedSessionCreate,
        agent_alias: Optional[str] = None,
        additional_env: Optional[Dict[str, str]] = None,
    ) -> client.V1Job:
        """Create Kubernetes job specification."""
        sanitized_name = sanitize_label(session_name)

        # Build environment variables
        env_vars = [
            client.V1EnvVar(name="SESSION_ID", value=session_id),
            client.V1EnvVar(name="DEEPSEEK_API_KEY", value=settings.deepseek_api_key),
            client.V1EnvVar(name="OPENAI_API_KEY", value=settings.openai_api_key),
        ]

        # Add additional environment variables
        if additional_env:
            for key, value in additional_env.items():
                env_vars.append(client.V1EnvVar(name=key, value=value))

        # Add authentication if provided
        if config.character_id:
            env_vars.append(
                client.V1EnvVar(name="CHARACTER_ID", value=config.character_id)
            )
        if config.token:
            env_vars.append(client.V1EnvVar(name="CAI_TOKEN", value=config.token))

        # Container specification
        container = client.V1Container(
            name="cai-advanced",
            image=settings.cai_image,
            env=env_vars,
            image_pull_policy="Always",
            command=["/bin/bash", "-c"],
            args=[command],
            volume_mounts=[
                client.V1VolumeMount(name="agents-config", mount_path="/config")
            ],
        )

        # Pod template
        template = client.V1PodTemplateSpec(
            metadata=client.V1ObjectMeta(
                labels={
                    "app": "cai-advanced",
                    "session-id": session_id,
                    "agent-alias": agent_alias or "default",
                }
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

        # Job specification
        return client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(
                name=job_name,
                labels={
                    "session-id": session_id,
                    "session-name": sanitized_name,
                    "app": "cai-advanced",
                    "agent-alias": agent_alias or "default",
                },
            ),
            spec=client.V1JobSpec(
                template=template,
                backoff_limit=3,
                ttl_seconds_after_finished=3600,  # Clean up after 1 hour
            ),
        )

    def get_session_progress(self, session_id: str) -> Dict[str, any]:
        """Get detailed progress information for a session."""
        try:
            # Find all jobs for this session
            jobs = self.batch_v1.list_namespaced_job(
                namespace=self.namespace, label_selector=f"session-id={session_id}"
            )

            progress = {
                "total_jobs": len(jobs.items),
                "completed_jobs": 0,
                "failed_jobs": 0,
                "running_jobs": 0,
                "pending_jobs": 0,
                "job_details": [],
            }

            for job in jobs.items:
                status = self.get_job_status(job.metadata.name)
                agent_alias = job.metadata.labels.get("agent-alias", "unknown")

                job_detail = {
                    "job_name": job.metadata.name,
                    "agent_alias": agent_alias,
                    "status": status,
                    "created": job.metadata.creation_timestamp.isoformat(),
                }

                progress["job_details"].append(job_detail)

                if status == "Completed":
                    progress["completed_jobs"] += 1
                elif status == "Failed":
                    progress["failed_jobs"] += 1
                elif status == "Running":
                    progress["running_jobs"] += 1
                else:
                    progress["pending_jobs"] += 1

            return progress
        except Exception as e:
            logger.error(f"Failed to get session progress: {str(e)}")
            return {"error": str(e)}

    def extract_session_results(self, session_id: str) -> Dict[str, any]:
        """Extract and aggregate results from all jobs in a session."""
        try:
            results = {
                "session_id": session_id,
                "flags_found": [],
                "vulnerabilities": [],
                "outputs": {},
                "cost_summary": {},
                "execution_summary": {},
            }

            # Get all pods for this session
            pods = self.core_v1.list_namespaced_pod(
                namespace=self.namespace, label_selector=f"session-id={session_id}"
            )

            for pod in pods.items:
                pod_name = pod.metadata.name
                agent_alias = pod.metadata.labels.get("agent-alias", "unknown")

                try:
                    # Get logs
                    logs = self.core_v1.read_namespaced_pod_log(
                        name=pod_name, namespace=self.namespace
                    )

                    results["outputs"][agent_alias] = logs

                    # Extract flags (for CTF)
                    flags = self._extract_flags_from_logs(logs)
                    results["flags_found"].extend(flags)

                    # Extract vulnerabilities
                    vulns = self._extract_vulnerabilities_from_logs(logs)
                    results["vulnerabilities"].extend(vulns)

                except Exception as e:
                    logger.error(f"Failed to get logs from pod {pod_name}: {str(e)}")
                    results["outputs"][agent_alias] = f"Error: {str(e)}"

            return results
        except Exception as e:
            logger.error(f"Failed to extract session results: {str(e)}")
            return {"error": str(e)}

    def _extract_flags_from_logs(self, logs: str) -> List[str]:
        """Extract CTF flags from logs."""
        import re

        flag_pattern = r"flag\{[^}]+\}"
        flags = re.findall(flag_pattern, logs, re.IGNORECASE)
        return list(set(flags))  # Remove duplicates

    def _extract_vulnerabilities_from_logs(self, logs: str) -> List[str]:
        """Extract vulnerability findings from logs."""
        import re

        vuln_patterns = [
            r"vulnerability.*found",
            r"exploit.*successful",
            r"CVE-\d{4}-\d+",
            r"SQL injection",
            r"XSS.*detected",
            r"buffer overflow",
            r"privilege escalation",
        ]

        vulnerabilities = []
        for pattern in vuln_patterns:
            matches = re.findall(pattern, logs, re.IGNORECASE)
            vulnerabilities.extend(matches)

        return list(set(vulnerabilities))  # Remove duplicates

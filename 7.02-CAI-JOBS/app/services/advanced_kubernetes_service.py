"""Advanced Kubernetes service with CAI integration features."""
import logging
from typing import Dict, List, Optional, Tuple

from ..config import settings
from ..models.advanced import (
    AdvancedSessionCreate,
    AgentType,
    ModelType,
    QueueItem,
    SessionMode,
)
from ..models.mcp import MCPServerConfig
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

    def create_manifestwork_for_session(
        self,
        session_id: str,
        config: AdvancedSessionCreate,
        manifest_path: str = "manifest/managedmanifest.yaml",
        runtime_map: Optional[dict] = None,
    ) -> dict:
        """
        Dynamically load managedmanifest.yaml, substitute $VALUE fields, and create ManifestWork in cluster.
        """
        import yaml
        from app.utils.manifest_substitute import substitute_manifest_vars

        # Load manifest YAML
        with open(manifest_path, "r") as f:
            manifest_data = yaml.safe_load(f)

        # Build runtime map for $VALUE substitution
        if runtime_map is None:
            runtime_map = {
                "SESSION_NAME": f"cai-session-{session_id[:8]}",
                "HUB_NAMESPACE": settings.managed_cluster_namespace,
                "TARGET_NAMESPACE": self.namespace,
                "JOB_NAME": f"cai-job-{session_id[:8]}",
                "AGENT_ALIAS": "default",
                "SERVICE_ACCOUNT": "default",
                "IMAGE": getattr(settings, "cai_image", "neptune1212/kali-cai:amd64"),
                "SESSION_ID": session_id,
                "DEEPSEEK_API_KEY": getattr(settings, "deepseek_api_key", ""),
                "OPENAI_API_KEY": getattr(settings, "openai_api_key", ""),
                "LITELLM_DISABLE_AUTH": "true",
                "WEBHOOK_URL": getattr(settings, "webhook_url", ""),
                "CHARACTER_ID": getattr(config, "character_id", "") if hasattr(config, "character_id") else "",
                "CAI_TOKEN": getattr(config, "token", "") if hasattr(config, "token") else "",
                "ARGS": self._build_cai_command(
                    config.prompt if hasattr(config, 'prompt') else "default prompt",
                    AgentType.REDTEAM if hasattr(config, 'agent_type') else AgentType.REDTEAM,
                    ModelType.DEEPSEEK_CHAT if hasattr(config, 'model') else ModelType.DEEPSEEK_CHAT,
                    config,
                    session_id
                ),
            }

        # Substitute all $VALUE and $VARNAME fields recursively
        manifestwork = substitute_manifest_vars(manifest_data, runtime_map)

        # Create ManifestWork in cluster using CustomObjectsApi
        from kubernetes.client import CustomObjectsApi
        custom_api = CustomObjectsApi()
        try:
            result = custom_api.create_namespaced_custom_object(
                group="work.open-cluster-management.io",
                version="v1",
                namespace=settings.managed_cluster_namespace,
                plural="manifestworks",
                body=manifestwork
            )
            logger.info(f"Created ManifestWork {manifestwork['metadata']['name']} in cluster.")
            return result
        except Exception as e:
            logger.error(f"Failed to create ManifestWork: {str(e)}")
            raise

    def _create_parallel_session(
        self, session_id: str, config: AdvancedSessionCreate
    ) -> Tuple[List[str], SessionMode]:
        """Create parallel execution session using ManifestWork."""
        job_names = []

        for i, agent_config in enumerate(config.parallel_agents):
            job_name = f"cai-parallel-{session_id[:8]}-{i}"

            # Build agent-specific runtime map
            runtime_map = {
                "SESSION_NAME": f"cai-session-{session_id[:8]}-{i}",
                "HUB_NAMESPACE": settings.managed_cluster_namespace,
                "TARGET_NAMESPACE": self.namespace,
                "JOB_NAME": job_name,
                "AGENT_ALIAS": agent_config.alias or agent_config.name,
                "SERVICE_ACCOUNT": "default",
                "IMAGE": getattr(settings, "cai_image", "neptune1212/kali-cai:amd64"),
                "SESSION_ID": f"{session_id}-{i}",
                "DEEPSEEK_API_KEY": getattr(settings, "deepseek_api_key", ""),
                "OPENAI_API_KEY": getattr(settings, "openai_api_key", ""),
                "LITELLM_DISABLE_AUTH": "true",
                "WEBHOOK_URL": getattr(settings, "webhook_url", ""),
                "CHARACTER_ID": getattr(config, "character_id", "") if hasattr(config, "character_id") else "",
                "CAI_TOKEN": getattr(config, "token", "") if hasattr(config, "token") else "",
                "ARGS": self._build_cai_command(
                    agent_config.initial_prompt or config.prompt,
                    agent_config.agent_type,
                    agent_config.model,
                    config,
                    f"{session_id}-{i}"
                ),
            }

            manifestwork = self.create_manifestwork_for_session(session_id, config, runtime_map=runtime_map)
            job_names.append(manifestwork['metadata']['name'])
            logger.info(
                f"Created ManifestWork {manifestwork['metadata']['name']} for agent {agent_config.name}"
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

# Execute CAI with queue and save results before quitting
echo '/save /tmp/queue_results.json' > /tmp/cai_commands.txt
echo '/quit' >> /tmp/cai_commands.txt
cat /tmp/cai_commands.txt | cai --yaml /config/agents.yml

# Capture results
if [ -d /home/kali/logs ]; then
  LOGFILE=$(find /home/kali/logs -name "cai_*.jsonl" -type f 2>/dev/null | head -1)
  if [ -n "$LOGFILE" ]; then
    echo "LOG_FILE_PATH: $LOGFILE"
    cat "$LOGFILE" > /tmp/job_logs_content
  fi
fi
# Check if results file was created
if [ -f /tmp/queue_results.json ]; then
  echo "Results saved to /tmp/queue_results.json"
fi
"""

        # Build runtime map for queue
        runtime_map = {
            "SESSION_NAME": f"cai-session-{session_id[:8]}",
            "HUB_NAMESPACE": settings.managed_cluster_namespace,
            "TARGET_NAMESPACE": self.namespace,
            "JOB_NAME": job_name,
            "AGENT_ALIAS": "default",
            "SERVICE_ACCOUNT": "default",
            "IMAGE": getattr(settings, "cai_image", "neptune1212/kali-cai:amd64"),
            "SESSION_ID": session_id,
            "DEEPSEEK_API_KEY": getattr(settings, "deepseek_api_key", ""),
            "OPENAI_API_KEY": getattr(settings, "openai_api_key", ""),
            "LITELLM_DISABLE_AUTH": "true",
            "WEBHOOK_URL": getattr(settings, "webhook_url", ""),
            "CHARACTER_ID": getattr(config, "character_id", "") if hasattr(config, "character_id") else "",
            "CAI_TOKEN": getattr(config, "token", "") if hasattr(config, "token") else "",
            "ARGS": queue_command,
        }

        manifestwork = self.create_manifestwork_for_session(session_id, config, runtime_map=runtime_map)
        logger.info(f"Created ManifestWork {manifestwork['metadata']['name']} for queue session")

        return [manifestwork['metadata']['name']], SessionMode.QUEUE

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

# Execute CAI with CTF configuration and save results before quitting
echo '/save /tmp/ctf_results.json' > /tmp/cai_commands.txt
echo '/quit' >> /tmp/cai_commands.txt
cat /tmp/ctf_prompt.txt /tmp/cai_commands.txt | cai

# Extract flags and save results
if [ -d /home/kali/logs ]; then
  LOGFILE=$(find /home/kali/logs -name "cai_*.jsonl" -type f 2>/dev/null | head -1)
  if [ -n "$LOGFILE" ]; then
    echo "LOG_FILE_PATH: $LOGFILE"
    # Extract flags
    grep -i "flag{{" "$LOGFILE" > /tmp/flags_found.txt || true
    cat "$LOGFILE" > /tmp/job_logs_content
  fi
fi
# Check if results file was created
if [ -f /tmp/ctf_results.json ]; then
  echo "CTF results saved to /tmp/ctf_results.json"
fi
"""

        # Build runtime map for CTF
        runtime_map = {
            "SESSION_NAME": f"cai-session-{session_id[:8]}",
            "HUB_NAMESPACE": settings.managed_cluster_namespace,
            "TARGET_NAMESPACE": self.namespace,
            "JOB_NAME": job_name,
            "AGENT_ALIAS": "default",
            "SERVICE_ACCOUNT": "default",
            "IMAGE": getattr(settings, "cai_image", "neptune1212/kali-cai:amd64"),
            "SESSION_ID": session_id,
            "DEEPSEEK_API_KEY": getattr(settings, "deepseek_api_key", ""),
            "OPENAI_API_KEY": getattr(settings, "openai_api_key", ""),
            "LITELLM_DISABLE_AUTH": "true",
            "WEBHOOK_URL": getattr(settings, "webhook_url", ""),
            "CHARACTER_ID": getattr(config, "character_id", "") if hasattr(config, "character_id") else "",
            "CAI_TOKEN": getattr(config, "token", "") if hasattr(config, "token") else "",
            "ARGS": ctf_command,
        }

        manifestwork = self.create_manifestwork_for_session(session_id, config, runtime_map=runtime_map)
        logger.info(f"Created ManifestWork {manifestwork['metadata']['name']} for CTF session {ctf.ctf_name}")

        return [manifestwork['metadata']['name']], SessionMode.CTF

    def _create_single_session(
        self, session_id: str, config: AdvancedSessionCreate
    ) -> str:
        """Create single agent session using ManifestWork."""
        manifestwork = self.create_manifestwork_for_session(session_id, config)
        job_name = manifestwork['metadata']['name']
        logger.info(f"Created ManifestWork {job_name} for single session")
        return job_name

    def _build_cai_command(
        self,
        prompt: str,
        agent_type: AgentType,
        model: ModelType,
        config: AdvancedSessionCreate,
        session_id: str,
    ) -> str:
        """Build CAI command with advanced features."""
        # Prefer agent-specific MCP overrides when provided, otherwise fall back.
        mcp_servers = self._select_mcp_for_agent(agent_type, config)
        mcp_block = self._render_mcp_load_commands(
            mcp_servers, agent_type=agent_type.value
        )
        command_parts = [
            "source /home/kali/cai/bin/activate",
            "",
            "# Set up environment variables",
            f"export CAI_MODEL={model.value}",
            f"export SESSION_ID={session_id}",
            "export CAI_INTERACTIVE=false",
            "export CAI_STREAM=false",
            "export LITELLM_DISABLE_AUTH=true",
            "export DEEPSEEK_API_KEY=" + settings.deepseek_api_key,
            "export SCAN_RESULTS_PATH=\"${SCAN_RESULTS_PATH:-/tmp/scan_results.json}\"",
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
                prompt ,
                "save results to $SCAN_RESULTS_PATH",
                "/quit",
                "PROMPT_EOF",
                "",
            ]
        )

        # Prepare MCP preload commands
        command_parts.extend(
            [
                "# Create MCP preload file",
                "cat > /tmp/mcp_commands.txt << 'MCP_EOF'",
                mcp_block,
                "MCP_EOF",
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
                "cat /tmp/mcp_commands.txt /tmp/cai_prompt.txt | cai",
                "if [ -d /home/kali/logs ]; then",
                "  LOGFILE=$(find /home/kali/logs -name 'cai_*.jsonl' -type f 2>/dev/null | head -1)",
                '  if [ -n "$LOGFILE" ]; then',
                '    echo "LOG_FILE_PATH: $LOGFILE"',
                '    cat "$LOGFILE" > /tmp/job_logs_content',
                "    # Extract specific patterns",
                "    grep -i 'vulnerability\\|exploit\\|flag{' \"$LOGFILE\" > /tmp/findings.txt || true",
                "  fi",
                "fi",
                "# Check if results file was created",
                "if [ -f \"$SCAN_RESULTS_PATH\" ]; then",
                "  echo 'Scan results saved to ' $SCAN_RESULTS_PATH",
                "  # Send results to webhook before marking task completed",
                "  curl -X POST -H 'Content-Type: application/json' --data-binary @$SCAN_RESULTS_PATH $WEBHOOK_URL/$SESSION_ID || echo 'Webhook send failed'",
                "  sleep 200",
                "fi",
            ]
        )

        return "\n".join(command_parts)

    @staticmethod
    def _select_mcp_for_agent(
        agent_type: AgentType, config: AdvancedSessionCreate
    ) -> Optional[List[MCPServerConfig]]:
        """Select MCP servers for a given agent, honoring overrides."""

        if config.mcp_agent_overrides:
            for mapping in config.mcp_agent_overrides:
                if mapping.agent_type == agent_type:
                    return mapping.mcp_servers

        return config.mcp_servers

    def _build_queue_from_items(self, queue_items: List[QueueItem]) -> str:
        """Build queue file content from queue items."""
        lines = ["# Auto-generated queue file"]

        for item in queue_items:
            if item.description:
                lines.append(f"# {item.description}")

            if item.agent_type:
                lines.append(f"/agent {item.agent_type.value}")

            lines.append(item.command)
            lines.append("")

        return "\n".join(lines)

    def get_session_progress(self, session_id: str) -> Dict[str, any]:
        """Get detailed progress information for a session using ManifestWork."""
        try:
            from kubernetes.client import CustomObjectsApi
            custom_api = CustomObjectsApi()
            
            # Construct ManifestWork name
            manifestwork_name = f"cai-session-{session_id[:8]}"
            
            # Get ManifestWork
            manifestwork = custom_api.get_namespaced_custom_object(
                group="work.open-cluster-management.io",
                version="v1",
                namespace=settings.managed_cluster_namespace,
                plural="manifestworks",
                name=manifestwork_name
            )
            
            progress = {
                "session_id": session_id,
                "manifestwork_name": manifestwork_name,
                "total_manifests": len(manifestwork.get('spec', {}).get('workload', {}).get('manifests', [])),
                "applied_manifests": 0,
                "available_manifests": 0,
                "manifest_details": [],
            }
            
            resource_status = manifestwork.get('status', {}).get('resourceStatus', {}).get('manifests', [])
            for manifest in resource_status:
                conditions = manifest.get('conditions', [])
                applied = any(c.get('type') == 'Applied' and c.get('status') == 'True' for c in conditions)
                available = any(c.get('type') == 'Available' and c.get('status') == 'True' for c in conditions)
                
                if applied:
                    progress["applied_manifests"] += 1
                if available:
                    progress["available_manifests"] += 1
                
                detail = {
                    "kind": manifest.get('resourceMeta', {}).get('kind'),
                    "name": manifest.get('resourceMeta', {}).get('name'),
                    "namespace": manifest.get('resourceMeta', {}).get('namespace'),
                    "applied": applied,
                    "available": available,
                }
                progress["manifest_details"].append(detail)
                logger.info(f"Manifest detail: {detail}")
            
            return progress
        except Exception as e:
            logger.error(f"Failed to get session progress: {str(e)}")
            return {"error": str(e)}

    def extract_session_results(self, session_id: str) -> Dict[str, any]:
        """Extract results information for a session from ManifestWork."""
        try:
            from kubernetes.client import CustomObjectsApi
            custom_api = CustomObjectsApi()
            
            # Construct ManifestWork name
            manifestwork_name = f"cai-session-{session_id[:8]}"
            
            # Get ManifestWork
            manifestwork = custom_api.get_namespaced_custom_object(
                group="work.open-cluster-management.io",
                version="v1",
                namespace=settings.managed_cluster_namespace,
                plural="manifestworks",
                name=manifestwork_name
            )
            
            results = {
                "session_id": session_id,
                "manifestwork_name": manifestwork_name,
                "manifestwork_status": manifestwork.get('status', {}),
                "note": "Job results are sent to webhook URL. Check webhook service for detailed results.",
            }
            
            return results
        except Exception as e:
            logger.error(f"Failed to extract session results: {str(e)}")
            return {"error": str(e)}

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

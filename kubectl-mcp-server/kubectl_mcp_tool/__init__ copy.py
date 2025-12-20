"""
Kubectl MCP Tool - A Model Context Protocol server for Kubernetes.
"""

__version__ = "1.1.1"

# Import minimized implementations
from . import enhanced_json_fix, minimal_wrapper, simple_ping, taskgroup_fix

__all__ = ["minimal_wrapper", "simple_ping", "enhanced_json_fix", "taskgroup_fix"]

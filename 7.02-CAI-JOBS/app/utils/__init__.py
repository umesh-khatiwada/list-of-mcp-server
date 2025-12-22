"""Utility functions for the application."""
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


def sanitize_label(value: str) -> str:
    """Sanitize a string to be used as a Kubernetes label.

    Args:
        value: The string value to sanitize

    Returns:
        A sanitized string suitable for Kubernetes labels
    """
    # Replace spaces and invalid chars with hyphens
    sanitized = value.replace(" ", "-").replace("_", "-")
    # Remove any character that's not alphanumeric, hyphen, or dot
    sanitized = "".join(c for c in sanitized if c.isalnum() or c in ["-", "."])
    # Ensure it starts and ends with alphanumeric
    sanitized = sanitized.strip("-.")
    # Limit to 63 characters (K8s label limit)
    return sanitized[:63]

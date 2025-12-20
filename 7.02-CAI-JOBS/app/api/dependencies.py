"""API dependencies."""
from ..services import KubernetesService


def get_kubernetes_service() -> KubernetesService:
    """Get Kubernetes service instance.

    Returns:
        KubernetesService instance
    """
    return KubernetesService()

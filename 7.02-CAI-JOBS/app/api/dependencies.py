"""API dependencies."""
from ..services import AdvancedKubernetesService


def get_kubernetes_service() -> AdvancedKubernetesService:
    """Get Kubernetes service instance.

    Returns:
        AdvancedKubernetesService instance
    """
    return AdvancedKubernetesService()

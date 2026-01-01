from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

# In-memory store for cluster metrics
# Format: { "cluster_name": { "cpu_usage": 10.5, "memory_usage": 45.2, "last_updated": datetime } }
cluster_metrics_store: Dict[str, Dict] = {}

def update_cluster_metrics(cluster_name: str, metrics: Dict):
    """Update metrics for a specific cluster."""
    metrics["last_updated"] = datetime.now()
    cluster_metrics_store[cluster_name] = metrics
    logger.info(f"Updated metrics for cluster: {cluster_name}")

def get_cluster_metrics(cluster_name: str) -> Optional[Dict]:
    """Get metrics for a specific cluster."""
    return cluster_metrics_store.get(cluster_name)

def get_all_clusters() -> Dict[str, Dict]:
    """Get metrics for all clusters."""
    return cluster_metrics_store

def get_optimal_cluster() -> str:
    """
    Find the cluster with the most available resources.
    For simplicity, we'll choose the one with the lowest CPU usage.
    Defaults to 'kind-manifest2' if no data is available or all are equal.
    """
    if not cluster_metrics_store:
        logger.warning("No cluster metrics available. Defaulting to east.")
        return "east"
        
    best_cluster = None
    lowest_cpu = float('inf')
    
    for name, metrics in cluster_metrics_store.items():
        cpu = metrics.get('cpu_usage', 100)
        if cpu < lowest_cpu:
            lowest_cpu = cpu
            best_cluster = name
            
    if best_cluster:
        logger.info(f"Selected optimal cluster: {best_cluster} with CPU: {lowest_cpu}%")
        return best_cluster
    
    return "east"

from datetime import datetime
from typing import Dict, List, Optional, Any
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



def get_all_clusters() -> Dict[str, Any]:
    """Get metrics for all clusters with current server timestamp."""
    return {
        "clusters": cluster_metrics_store,
        "server_time": datetime.now().isoformat()
    }

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
    best_cluster = None
    max_score = -1.0
    
    for name, metrics in cluster_metrics_store.items():
        cpu_usage_pct = metrics.get('cpu_usage', 100)
        cpu_count = metrics.get('cpu_count', 1)
        memory_available_bytes = metrics.get('memory_available', 0)
        
        # Calculate available resources
        available_cpu = cpu_count * (1 - (cpu_usage_pct / 100.0))
        available_memory_gb = memory_available_bytes / (1024**3)
        
        # Scoring: Product of CPU and Memory (favors balanced/large nodes)
        # Using product ensures that if either is near-zero, the score is near-zero.
        score = available_cpu * available_memory_gb
        
        logger.debug(f"Cluster {name}: CPU={available_cpu:.2f}, Mem={available_memory_gb:.2f}GB, Score={score:.2f}")
        
        if score > max_score:
            max_score = score
            best_cluster = name
            
    if best_cluster:
        logger.info(f"Selected optimal cluster: {best_cluster} (Score: {max_score:.2f})")
        return best_cluster
    
    return "east"

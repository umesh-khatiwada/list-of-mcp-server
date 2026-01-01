from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any

from app.services.cluster_store import update_cluster_metrics, get_all_clusters

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

class ClusterMetrics(BaseModel):
    cluster_name: str
    cpu_usage: float
    memory_usage: float
    memory_total: int
    memory_available: int
    timestamp: str

@router.post("/metrics")
async def receive_metrics(metrics: ClusterMetrics):
    """Receive and store metrics from a spoke cluster."""
    update_cluster_metrics(metrics.cluster_name, metrics.dict())
    return {"status": "received", "cluster": metrics.cluster_name}

@router.get("/clusters")
async def list_clusters():
    """Get status of all monitored clusters."""
    return get_all_clusters()

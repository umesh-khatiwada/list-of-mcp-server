import os
import time
import requests
import psutil
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("MonitorAgent")

# Configuration
CLUSTER_NAME = os.getenv("CLUSTER_NAME", "unknown-cluster")
HUB_URL = os.getenv("HUB_URL", "http://localhost:8000")
REPORT_INTERVAL = int(os.getenv("REPORT_INTERVAL", "30"))

def collect_metrics():
    """Collect system metrics."""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    
    return {
        "cluster_name": CLUSTER_NAME,
        "cpu_usage": cpu_percent,
        "cpu_count": psutil.cpu_count(),
        "memory_usage": memory.percent,
        "memory_total": memory.total,
        "memory_available": memory.available,
        "timestamp": datetime.now().isoformat()
    }

def send_metrics(metrics):
    """Send metrics to the Hub."""
    try:
        url = f"{HUB_URL}/api/monitoring/metrics"
        response = requests.post(url, json=metrics)
        if response.status_code == 200:
            logger.info(f"Metrics sent successfully for {CLUSTER_NAME}")
        else:
            logger.error(f"Failed to send metrics: {response.status_code} - {response.text}")
    except Exception as e:
        logger.error(f"Error sending metrics: {str(e)}")

def main():
    logger.info(f"Starting Monitoring Agent for cluster: {CLUSTER_NAME}")
    logger.info(f"Reporting to Hub: {HUB_URL} every {REPORT_INTERVAL} seconds")
    
    while True:
        try:
            metrics = collect_metrics()
            logger.info(f"Collected metrics: CPU {metrics['cpu_usage']}%, Mem {metrics['memory_usage']}%")
            send_metrics(metrics)
        except Exception as e:
            logger.error(f"Error in main loop: {str(e)}")
        
        time.sleep(REPORT_INTERVAL)

if __name__ == "__main__":
    main()

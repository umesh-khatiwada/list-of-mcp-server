from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, RootModel # RootModel is no longer strictly needed but keeping for now
from kubernetes import client, config
import uvicorn
import logging
import json

app = FastAPI()

# Configure logging for the FastAPI application
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load in-cluster config
try:
    config.load_incluster_config()
    logger.info("Loaded in-cluster Kubernetes config.")
except config.ConfigException:
    config.load_kube_config()
    logger.info("Loaded local Kubernetes config (kube_config).")
except Exception as e:
    logger.error(f"Failed to load Kubernetes config: {e}")
    raise

core_v1 = client.CoreV1Api()
apps_v1 = client.AppsV1Api()


class InstructionRequest(BaseModel):
    instruction: str
    params: dict


# Removed RawCommandString model as Lambda now sends direct JSON object


@app.post("/mcp/execute")
async def execute_instruction(req: InstructionRequest): # <--- CHANGE THIS PARAMETER BACK
    try:
        # No need for json.loads() here, FastAPI handles parsing into InstructionRequest
        instruction = req.instruction
        params = req.params

        logger.info(f"Received instruction: {instruction} with params: {params}")

        if instruction == "k8s_resource_status":
            resource = params.get("resource_type", "pods")
            namespace = params.get("namespace", "default")
            if resource == "pods":
                pods = core_v1.list_namespaced_pod(namespace=namespace)
                return {"status": "success", "result": {"pods": [{"name": pod.metadata.name, "status": pod.status.phase} for pod in pods.items]}}
            elif resource == "services":
                svcs = core_v1.list_namespaced_service(namespace=namespace)
                return {"status": "success", "result": {"services": [
                    {
                        "name": svc.metadata.name,
                        "cluster_ip": svc.spec.cluster_ip,
                        "ports": [
                            {
                                "name": port.name,
                                "port": port.port,
                                "protocol": port.protocol,
                                "target_port": port.target_port
                            } for port in svc.spec.ports
                        ] if svc.spec.ports else []
                    } for svc in svcs.items
                ]}}
            else:
                logger.warning(f"Unsupported resource type for k8s_resource_status: {resource}")
                return JSONResponse(status_code=400, content={"error": f"Unsupported resource: {resource}"})

        elif instruction == "describe_pod":
            namespace = params.get("namespace", "default")
            pod_name = params.get("pod_name")
            if not pod_name:
                logger.warning("Missing 'pod_name' for describe_pod instruction.")
                return JSONResponse(status_code=400, content={"error": "Missing 'pod_name' parameter."})
            pod = core_v1.read_namespaced_pod(name=pod_name, namespace=namespace)
            return {"status": "success", "result": {"pod": pod.to_dict()}}

        elif instruction == "get_pod_logs":
            namespace = params.get("namespace", "default")
            pod_name = params.get("pod_name")
            container = params.get("container")
            if not pod_name:
                logger.warning("Missing 'pod_name' for get_pod_logs instruction.")
                return JSONResponse(status_code=400, content={"error": "Missing 'pod_name' parameter."})
            logs = core_v1.read_namespaced_pod_log(name=pod_name, namespace=namespace, container=container)
            return {"status": "success", "result": {"logs": logs}}

        elif instruction == "get_pod":
            namespace = params.get("namespace", "default")
            pod_name = params.get("pod_name")
            if pod_name:
                pod = core_v1.read_namespaced_pod(name=pod_name, namespace=namespace)
                return {"status": "success", "result": {"pod": {"name": pod.metadata.name, "status": pod.status.phase}}}
            else:
                pods = core_v1.list_namespaced_pod(namespace=namespace)
                return {"status": "success", "result": {"pods": [{"name": pod.metadata.name, "status": pod.status.phase} for pod in pods.items]}}

        else:
            logger.warning(f"Unknown instruction received: {instruction}")
            return JSONResponse(status_code=400, content={"error": f"Unknown instruction: {instruction}"})

    except json.JSONDecodeError as e: # This block might not be hit now, but good to keep for robustness
        logger.error(f"JSON decoding error: {e}")
        return JSONResponse(status_code=400, content={"error": f"Invalid JSON format in request body: {e}"})
    except client.ApiException as e:
        logger.error(f"Kubernetes API error (status {e.status}): {e.reason} - {e.body.decode('utf-8') if e.body else 'No response body'}")
        return JSONResponse(status_code=e.status, content={"error": f"Kubernetes API error: {e.reason} - {e.body.decode('utf-8') if e.body else 'No response body'}"})
    except Exception as e:
        logger.exception("An unexpected error occurred during instruction execution.")
        return JSONResponse(status_code=500, content={"error": "An internal server error occurred. Check server logs for details."})


# For local testing
if __name__ == "__main__":
    uvicorn.run("app.server:app", host="0.0.0.0", port=8000)
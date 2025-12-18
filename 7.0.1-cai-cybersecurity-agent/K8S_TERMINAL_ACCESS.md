# Kubernetes Terminal Access Guide

## Problem Fixed
The "EOF when reading a line" error has been resolved. The orchestrator now runs in **service-only mode** by default in Kubernetes, which means it doesn't try to read from stdin.

## Architecture
- **Service Mode (Default in K8s)**: The orchestrator runs as an API service only, without trying to read from stdin
- **Interactive Mode (Local Development)**: Can be enabled to allow terminal input for testing

## Configuration

### Running in Service Mode (K8s - Default)
No stdin required. The orchestrator exposes the registry API on port 8000.

Environment variable in k8s/orchestrator-agent.yaml:
```yaml
- name: ORCHESTRATOR_INTERACTIVE_MODE
  value: "false"  # Service-only mode (no stdin)
```

### Enabling Interactive Mode (Local Development)
To enable terminal input for local testing:

```bash
export ORCHESTRATOR_INTERACTIVE_MODE=true
python orchestrator-agent/orchestrator.py
```

Or in Kubernetes (requires TTY):
```yaml
- name: ORCHESTRATOR_INTERACTIVE_MODE
  value: "true"
```

## Using the Orchestrator in Kubernetes

### 1. Register Agents via API
```bash
# Forward the orchestrator service port
kubectl port-forward svc/orchestrator-agent 8000:8000

# Register an agent
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "cybersecurity-agent",
    "url": "http://cybersecurity-agent:9003"
  }'

# List registered agents
curl http://localhost:8000/agents
```

### 2. Access Pod Terminal (for debugging)
```bash
# Get pod name
kubectl get pods -l app=orchestrator-agent

# Access the pod's shell
kubectl exec -it <pod-name> -- /bin/bash

# View logs
kubectl logs <pod-name> -f
```

### 3. Enable Interactive Mode in Pod (Advanced)
If you need to interact with the orchestrator via stdin in a pod:

```bash
# Set environment variable and access with TTY
kubectl set env deployment/orchestrator-agent ORCHESTRATOR_INTERACTIVE_MODE=true

# Access with interactive terminal
kubectl exec -it <pod-name> -- python /app/orchestrator.py
```

## API Endpoints

### Health Check
```bash
curl http://localhost:8000/health
```

### Register Agent
```bash
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "agent-name",
    "url": "http://agent-url:port"
  }'
```

### List Agents
```bash
curl http://localhost:8000/agents
```

### Unregister Agent
```bash
curl -X DELETE http://localhost:8000/unregister/agent-name
```

## Troubleshooting

### "EOF when reading a line" Error
This error occurs when the application tries to read from stdin in a containerized environment without TTY.

**Solution**: Ensure `ORCHESTRATOR_INTERACTIVE_MODE` is set to `false` (default) in k8s deployments.

### Logs Show "Running in service-only mode"
This is normal behavior in Kubernetes. The orchestrator is functioning correctly as an API service.

### Need to Send Commands
Use the registry API endpoints instead of stdin. All orchestrator functions are available via the REST API.

## Example: Complete Workflow

```bash
# 1. Deploy to Kubernetes
kubectl apply -f k8s/orchestrator-agent.yaml

# 2. Wait for pod to be ready
kubectl wait --for=condition=ready pod -l app=orchestrator-agent

# 3. Port forward the service
kubectl port-forward svc/orchestrator-agent 8000:8000 &

# 4. Register agents
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"name": "cybersecurity-agent", "url": "http://cybersecurity-agent:9003"}'

# 5. Check registered agents
curl http://localhost:8000/agents

# 6. View logs
kubectl logs -l app=orchestrator-agent -f
```

## Local Development

For local development with terminal input:

```bash
# Set interactive mode
export ORCHESTRATOR_INTERACTIVE_MODE=true

# Run the orchestrator
python orchestrator-agent/orchestrator.py

# Now you can type commands directly:
> analyze security vulnerabilities
```

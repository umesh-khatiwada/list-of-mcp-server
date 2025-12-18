#!/bin/bash

# Script to rebuild and deploy the fixed orchestrator-agent to Kubernetes

set -e

echo "=========================================="
echo "Rebuilding Orchestrator Agent (EOF Fix)"
echo "=========================================="

# Configuration
IMAGE_NAME="umesh1212/orchestrator-agent"
IMAGE_TAG="v11"
FULL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"

# Step 1: Build Docker image
echo ""
echo "Step 1: Building Docker image..."
docker build -t ${FULL_IMAGE} -f Dockerfile.local .
cd ..

# Step 2: Push to registry
echo ""
echo "Step 2: Pushing image to registry..."
docker push ${FULL_IMAGE}

# Step 3: Update Kubernetes deployment
echo ""
echo "Step 3: Updating Kubernetes deployment..."

# Update the image in the deployment
kubectl set image deployment/orchestrator-agent orchestrator-agent=${FULL_IMAGE}

# Or redeploy with the yaml
# kubectl delete -f k8s/orchestrator-agent.yaml
# kubectl apply -f k8s/orchestrator-agent.yaml

# Step 4: Wait for rollout
echo ""
echo "Step 4: Waiting for rollout to complete..."
kubectl rollout status deployment/orchestrator-agent

# Step 5: Check pod status
echo ""
echo "Step 5: Checking pod status..."
kubectl get pods -l app=orchestrator-agent

# Step 6: View logs
echo ""
echo "Step 6: Viewing recent logs..."
echo "----------------------------------------"
kubectl logs -l app=orchestrator-agent --tail=20

echo ""
echo "=========================================="
echo "✓ Deployment Complete!"
echo "=========================================="
echo ""
echo "To view live logs, run:"
echo "  kubectl logs -l app=orchestrator-agent -f"
echo ""
echo "To port-forward the service, run:"
echo "  kubectl port-forward svc/orchestrator-agent 8000:8000"
echo ""
echo "To register agents, use:"
echo '  curl -X POST http://localhost:8000/register \'
echo '    -H "Content-Type: application/json" \'
echo '    -d '\''{"name": "cybersecurity-agent", "url": "http://cybersecurity-agent:9003"}'\'''
echo ""

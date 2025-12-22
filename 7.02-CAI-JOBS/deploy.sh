#!/bin/bash

# Script to deploy the CAI Manager application to Kubernetes
# This script will deploy all necessary resources in the correct order

set -e

echo "=== CAI Manager Deployment Script ==="
echo

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is not installed or not in PATH"
    exit 1
fi

# Check if we're connected to a cluster
if ! kubectl cluster-info &> /dev/null; then
    echo "Error: Not connected to a Kubernetes cluster"
    exit 1
fi

echo "Current Kubernetes context:"
kubectl config current-context
echo

# Check if API keys secret exists
if ! kubectl get secret cai-api-keys &> /dev/null; then
    echo "⚠️  API keys secret not found!"
    echo "Please run './setup-api-keys.sh' first to configure your API keys"
    read -p "Continue deployment anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Deploy resources in order
echo "1. Deploying RBAC and Service Account..."
kubectl apply -f k8s/secrets.yaml
echo "✅ RBAC resources deployed"

echo "2. Deploying ConfigMaps..."
if [ -f k8s/agents-configmap.yaml ]; then
    kubectl apply -f k8s/agents-configmap.yaml
    echo "✅ ConfigMaps deployed"
else
    echo "⚠️  ConfigMaps file not found, skipping..."
fi

echo "3. Deploying Application..."
kubectl apply -f k8s/k8s.yaml
echo "✅ Application deployment created"

echo "4. Deploying Service..."
kubectl apply -f k8s/service.yaml
echo "✅ Service created"

echo
echo "=== Deployment Status ==="
echo "Checking deployment status..."

# Wait for deployment to be ready
kubectl rollout status deployment/cai-manager --timeout=120s

echo
echo "=== Pod Status ==="
kubectl get pods -l app=cai-manager

echo
echo "=== Service Status ==="
kubectl get services cai-manager

echo
echo "=== Deployment Complete ==="
echo "🎉 CAI Manager has been deployed successfully!"
echo
echo "Useful commands:"
echo "  View logs:     kubectl logs -l app=cai-manager -f"
echo "  Get pods:      kubectl get pods -l app=cai-manager"
echo "  Port forward:  kubectl port-forward service/cai-manager 8000:8000"
echo "  Delete all:    kubectl delete -f k8s/"
echo
echo "API will be available at: http://localhost:8000 (after port-forward)"
echo "Health check:            http://localhost:8000/api/health"

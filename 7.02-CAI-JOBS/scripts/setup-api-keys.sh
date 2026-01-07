#!/bin/bash

# Script to set up Kubernetes secrets for CAI API keys
# Run this script to configure your API keys for the CAI manager

set -e

echo "=== CAI Manager API Key Setup ==="
echo

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is not installed or not in PATH"
    exit 1
fi

# Check if we're connected to a cluster
if ! kubectl cluster-info &> /dev/null; then
    echo "Error: Not connected to a Kubernetes cluster"
    echo "Please ensure you have a valid kubeconfig"
    exit 1
fi

echo "Current Kubernetes context:"
kubectl config current-context
echo

# Prompt for API keys
read -p "Enter your DeepSeek API key (or press Enter to skip): " DEEPSEEK_KEY
read -p "Enter your OpenAI API key (or press Enter to skip): " OPENAI_KEY
read -p "Enter your Alias API key (or press Enter to skip): " ALIAS_KEY

# Validate at least one key is provided
if [ -z "$DEEPSEEK_KEY" ] && [ -z "$OPENAI_KEY" ] && [ -z "$ALIAS_KEY" ]; then
    echo "Error: At least one API key must be provided"
    exit 1
fi

# Create the secret
echo "Creating Kubernetes secret..."

kubectl create secret generic cai-api-keys \
    --from-literal=deepseek-api-key="${DEEPSEEK_KEY:-placeholder}" \
    --from-literal=openai-api-key="${OPENAI_KEY:-placeholder}" \
    --from-literal=alias-api-key="${ALIAS_KEY:-placeholder}" \
    --dry-run=client -o yaml | kubectl apply -f -

echo "✅ API keys secret created successfully!"
echo

# Verify the secret
echo "Verifying secret creation..."
if kubectl get secret cai-api-keys &> /dev/null; then
    echo "✅ Secret 'cai-api-keys' exists"
    kubectl get secret cai-api-keys -o yaml | grep -E "deepseek-api-key|openai-api-key|alias-api-key" | wc -l
    echo "   Found $(kubectl get secret cai-api-keys -o yaml | grep -E 'deepseek-api-key|openai-api-key|alias-api-key' | wc -l) API key entries"
else
    echo "❌ Failed to create secret"
    exit 1
fi

echo
echo "=== Next Steps ==="
echo "1. Deploy the application: kubectl apply -f k8s/"
echo "2. Check pod status: kubectl get pods -l app=cai-manager"
echo "3. View logs: kubectl logs -l app=cai-manager -f"
echo
echo "To update API keys later, run:"
echo "  kubectl delete secret cai-api-keys"
echo "  ./setup-api-keys.sh"

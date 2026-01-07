#!/bin/bash
set -e

# Configuration
HUB_CLUSTER="hub"
SPOKE_CLUSTERS=("east" "west")
MANAGER_IMAGE="cai-manager:latest"
MONITOR_IMAGE="cai-monitor:latest"

echo "🔹 Building CAI Job Manager image..."
docker build --no-cache -t $MANAGER_IMAGE .

echo "🔹 Building CAI Monitor Agent image..."
cd monitor_agent
docker build -t $MONITOR_IMAGE .
cd ..

echo "🔹 Loading images into Kind clusters..."

# Load Manager to Hub
echo "   Loading $MANAGER_IMAGE into cluster '$HUB_CLUSTER'..."
kind load docker-image $MANAGER_IMAGE --name $HUB_CLUSTER

# Load Monitor to Hub and Spokes (so it's available everywhere)
CLUSTERS=($HUB_CLUSTER "${SPOKE_CLUSTERS[@]}")
for cluster in "${CLUSTERS[@]}"; do
    echo "   Loading $MONITOR_IMAGE into cluster '$cluster'..."
    kind load docker-image $MONITOR_IMAGE --name $cluster
done

echo "✅ Images loaded successfully!"

echo "🔹 Applying Kubernetes manifests..."
# Apply manager manifests to Hub (includes RBAC, ServiceAccount, and Deployment)
kubectl --context kind-$HUB_CLUSTER apply -f k8s/k8s.yaml

# Optional: Restart deployments to pick up new images if they exist
echo "🔹 Restarting deployments..."

# Restart Manager on Hub
if kubectl --context kind-$HUB_CLUSTER get deployment cai-manager -n default > /dev/null 2>&1; then
    kubectl --context kind-$HUB_CLUSTER rollout restart deployment/cai-manager -n default
    echo "   Restarted cai-manager on $HUB_CLUSTER"
fi

# Restart Monitor on all clusters (if deployed)
for cluster in "${CLUSTERS[@]}"; do
    if kubectl --context kind-$cluster get deployment cai-monitor -n default > /dev/null 2>&1; then
        kubectl --context kind-$cluster rollout restart deployment/cai-monitor -n default
         echo "   Restarted cai-monitor on $cluster"
    fi
done

echo "🚀 Deployment refresh complete!"

#!/bin/bash
set -e

MANIFEST="k8s/monitor-agent.yaml"

deploy_monitor() {
    CLUSTER=$1
    echo "🚀 Deploying Monitor Agent to $CLUSTER..."
    
    # Create a temporary manifest with the correct cluster name
    sed "s/value: \"unknown-cluster\"/value: \"$CLUSTER\"/" $MANIFEST | kubectl --context kind-$CLUSTER apply -f -
    
    # Restart to ensure new config is picked up if it existed
    kubectl --context kind-$CLUSTER rollout restart deployment/cai-monitor
    
    echo "✅ Deployed to $CLUSTER"
}

# Deploy to East
deploy_monitor "east"

# Deploy to West
deploy_monitor "west"

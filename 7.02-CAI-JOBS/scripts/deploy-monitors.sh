#!/bin/bash
set -euo pipefail

# Configuration
MANIFEST="k8s/monitor-agent.yaml"
DEFAULT_CLUSTERS=("east" "west")

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
ORANGE='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warn() {
    echo -e "${ORANGE}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

check_dependencies() {
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl could not be found"
        exit 1
    fi
}

check_manifest() {
    if [[ ! -f "$MANIFEST" ]]; then
        log_error "Manifest file not found: $MANIFEST"
        exit 1
    fi
}

deploy_monitor() {
    local CLUSTER=$1
    log_info "🚀 Deploying Monitor Agent to ${YELLOW}$CLUSTER${NC}..."
    
    # Create a temporary manifest with the correct cluster name and apply it
    # We use a subshell to avoid leaving pipe failure status if sed fails, 
    # but with set -o pipefail, the pipeline will fail if any command fails.
    if sed "s/value: \"unknown-cluster\"/value: \"$CLUSTER\"/" "$MANIFEST" | kubectl --context "kind-$CLUSTER" apply -f -; then
         # Restart to ensure new config is picked up
        if kubectl --context "kind-$CLUSTER" rollout restart deployment/cai-monitor; then
             log_success "Deployed to $CLUSTER"
        else
             log_warn "Deployment restart failed for $CLUSTER (might be first deployment)"
        fi
    else
        log_error "Failed to apply manifest to $CLUSTER"
        return 1
    fi
}

main() {
    check_dependencies
    check_manifest

    local target_clusters=()

    if [[ $# -gt 0 ]]; then
        target_clusters=("$@")
    else
        target_clusters=("${DEFAULT_CLUSTERS[@]}")
    fi

    log_info "Starting deployment for clusters: ${target_clusters[*]}"

    local failed_clusters=()
    for cluster in "${target_clusters[@]}"; do
        if ! deploy_monitor "$cluster"; then
            failed_clusters+=("$cluster")
        fi
    done

    if [[ ${#failed_clusters[@]} -gt 0 ]]; then
        log_error "Deployment failed for: ${failed_clusters[*]}"
        exit 1
    else
        log_success "All deployments completed successfully!"
    fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi

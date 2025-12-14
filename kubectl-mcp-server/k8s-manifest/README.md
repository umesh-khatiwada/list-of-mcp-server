# Deployment Instructions for kubectl-mcp-server

## Prerequisites
1. Kubernetes cluster with kubectl access
2. Docker image: `umesh1212/kubectl-mcp-server:v1` available
3. Proper RBAC permissions to create resources

## Deployment Steps

### 1. Create the kubeconfig secret
First, you need to create a secret containing your kubeconfig:

```bash
# Method 1: Create secret from your kubeconfig file
kubectl create secret generic kubectl-mcp-server-kubeconfig \
  --from-file=config=$HOME/.kube/config \
  --namespace=default

# Method 2: Use the template file (edit kubeconfig-secret.yaml first)
# Replace the base64 content in kubeconfig-secret.yaml with your actual kubeconfig:
cat ~/.kube/config | base64 -w 0
kubectl apply -f kubeconfig-secret.yaml
```

### 2. Deploy the main application
```bash
# Apply all manifests
kubectl apply -f kubectl-mcp-server.yaml

# Or apply them individually
kubectl apply -f kubectl-mcp-server.yaml
```

### 3. Optional: Set up ingress for external access
```bash
# Edit ingress.yaml to configure your domain and TLS settings
kubectl apply -f ingress.yaml
```

## Verification

### Check deployment status
```bash
kubectl get pods -l app=kubectl-mcp-server
kubectl get svc kubectl-mcp-server-service
kubectl get deployment kubectl-mcp-server
```

### Check logs
```bash
kubectl logs -l app=kubectl-mcp-server -f
```

### Test the service
```bash
# Port forward to test locally
kubectl port-forward svc/kubectl-mcp-server-service 8080:80

# Test the endpoint
curl http://localhost:8080
```

## Configuration

### Environment Variables
- `TRANSPORT`: Communication transport (default: "sse")
- `PORT`: Server port (default: "8000")

### Resource Limits
- CPU: 100m (request) / 500m (limit)
- Memory: 128Mi (request) / 512Mi (limit)

### Auto-scaling
The HPA will scale the deployment between 1-5 replicas based on:
- CPU utilization > 70%
- Memory utilization > 80%

## Security Considerations

1. **RBAC**: The service account has broad kubectl permissions. Review and adjust the ClusterRole permissions based on your security requirements.

2. **Kubeconfig**: The kubeconfig is mounted as a secret. Ensure it has minimal required permissions.

3. **Network Policies**: Consider implementing network policies to restrict traffic.

4. **Image Security**: Regularly update the Docker image and scan for vulnerabilities.

## Troubleshooting

### Common Issues
1. **Pod not starting**: Check if the Docker image is accessible
2. **Permission errors**: Verify RBAC permissions
3. **Kubeconfig issues**: Ensure the secret is created correctly

### Debug Commands
```bash
# Describe pod for detailed information
kubectl describe pod -l app=kubectl-mcp-server

# Check events
kubectl get events --sort-by=.metadata.creationTimestamp

# Exec into the pod for debugging
kubectl exec -it deployment/kubectl-mcp-server -- /bin/bash
```

## Cleanup
```bash
# Remove all resources
kubectl delete -f kubectl-mcp-server.yaml
kubectl delete -f kubeconfig-secret.yaml
kubectl delete -f ingress.yaml

# Or delete by labels
kubectl delete all,secret,ingress,hpa,configmap -l app=kubectl-mcp-server
```

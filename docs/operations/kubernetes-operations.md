# Kubernetes operations

## Purpose
Operate the cluster in a cloud-neutral way using standard Kubernetes primitives.

## Preconditions
- `kubectl` installed and authenticated.
- Correct cluster context selected.
- Required namespaces created.

## Useful commands
```bash
kubectl get namespaces
kubectl get pods -A
kubectl get deployments -A
kubectl get services -A
kubectl get ingress -A
kubectl get hpa -A
kubectl logs deploy/backend -n hackathon-prod
kubectl describe pod <pod-name> -n hackathon-prod
```

## Verification
- Pod readiness is complete.
- Deployments have completed their rollout.
- Services route traffic to healthy endpoints.
- HPA is configured with valid min/max values and a working CPU target.

## Recovery
- Recreate a failed deployment if no recent revision is healthy.
- Inspect events and logs before any scale-up or config change.

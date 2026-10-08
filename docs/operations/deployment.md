# Deployment runbook

## Purpose
This runbook explains how to deploy the application using the same GHCR image artifact across DEV, TEST, STAGING, and PROD.

## Preconditions
- GitHub Actions workflow permissions configured for `contents: read` and `packages: write`.
- GitHub environment protection configured for `production`.
- A Kubernetes cluster is available and `kubectl` context is configured.
- Required namespace and secrets exist.

## Deployment model
1. Code changes land in a feature branch.
2. CI validates backend, frontend, and Docker image builds.
3. The same image is pushed to GHCR using the Git SHA tag.
4. The same image is promoted through Kubernetes environments.

## Commands
```bash
kubectl config get-contexts
kubectl get ns
kubectl -n hackathon-dev get pods
kubectl -n hackathon-dev rollout status deployment/backend
kubectl -n hackathon-dev rollout history deployment/backend
```

## Verification
- Pods are `Ready`.
- `/health` responds with HTTP 200.
- Frontend route responds successfully.
- Database connectivity is healthy.

## Failure scenarios
- Image pull errors: verify package permissions and registry authentication.
- CrashLoopBackOff: inspect pod logs and resource limits.
- Readiness failures: confirm secret references and database connectivity.

## Recovery
- Re-run the approved deployment using the same immutable image.
- Use the rollback runbook when a release is unhealthy.

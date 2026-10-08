# Environment management

## Purpose
Maintain separation and configuration across DEV, TEST, STAGING, and PROD.

## Environment model
- DEV: lower resource requests, lower replica counts, development-safe defaults.
- TEST: isolated database and validation workload.
- STAGING: production-like settings and health checks.
- PROD: stricter resources, autoscaling, and approval-based deployment.

## Configuration pattern
Use Kubernetes namespaces and environment-specific values files or ConfigMaps to set:
- replica counts
- resource requests and limits
- ingress rules
- database connection references
- secrets
- autoscaling thresholds

## Verification
- Namespace exists.
- Deployment uses the expected image tag.
- Secret values are injected correctly.
- Services and ingress route traffic as expected.

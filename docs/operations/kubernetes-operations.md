# Kubernetes operations

Validate overlays offline with kubectl kustomize, or run
python scripts/validate_ops.py for all four environments. Rendering checks do
not prove API-server admission, ingress routing, TLS, image pulls or autoscaling.
Never apply rendered placeholder images/hosts. Use the approved deployment
workflow and environment-scoped credentials described in deployment.md.

Deployments use non-root users, RuntimeDefault seccomp, dropped capabilities,
no privilege escalation, no service-account token mount, startup/liveness/readiness
HTTP probes, requests/limits, rolling updates, a progress deadline and five
retained revisions. Probes check process liveness, not database access.

Use approved namespace-scoped read-only diagnostics: get pods, events,
deployments, services and HPA; describe deployment/backend; inspect migration
Job status. Avoid dumping Secret values. HPA requires metrics-server and
appropriate cluster capacity. Preserve failed Jobs until diagnostics are done.

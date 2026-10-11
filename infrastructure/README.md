# Infrastructure overview

OPS-001 provides Docker/Compose, pinned GitHub Actions, Kustomize overlays,
PostgreSQL recovery safety scripts and operational runbooks. See
../docs/operations/OPS-001-INTEGRATION-REVIEW.md for verified results and limits.

Local Compose preserves the existing radar_postgres_data volume and PostgreSQL
host port 5433. It loads backend/.env and does not migrate automatically.
Deployments are manual, use protected-branch CI/publisher provenance, and migrate
with a one-shot Job before rolling out the same SHA-tagged images. Namespace,
Secrets, RBAC, ingress, TLS, external DB and production approval protection are
administrator prerequisites. No live deployment is validated here.

Prometheus configuration assumes an external blackbox exporter; it does not
install monitoring. Recovery scripts refuse existing targets and do not provide
backup scheduling/encryption/retention services. Coordinate those areas with
open DEVOPS-007 through DEVOPS-010 PRs rather than replacing their work.

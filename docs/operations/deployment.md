# Deployment runbook

## Preconditions and approval

No workflow deploys on a PR or push. Deployment requires an explicit manual
workflow dispatch and approval for the target environment. Configure GitHub
production required reviewers, prevent self-review, and restrict environment
branches to main. Use develop for development/test/staging. Branch protection
must require CI without granting bypass rights to these workflows. Repository
settings and environment protection have not been verified by local validation.

Provision a compatible Kubernetes cluster (workflows pin kubectl v1.36.1; check
client/server version skew), ingress-nginx, metrics-server for HPA, and separate
PostgreSQL databases per environment. Do not use the local development database.
Use a namespace-scoped service account that can manage Jobs, Deployments,
Services, ConfigMaps, Ingresses and HPAs, observe rollouts, and read only the named Secret
resources. It does not require cluster-admin or namespace creation privileges.
The namespace must already exist: hackathon-dev/test/staging/prod.

For each namespace, securely provision:

- hackathon-db-secret: DATABASE_URL (postgresql+psycopg:// connection).
- hackathon-app-secret: SECRET_KEY (random, at least 32 characters).
- ghcr-creds: registry pull credentials for the deployed packages.
- A TLS Secret matching the configured environment TLS_SECRET variable.

Set GitHub environment secrets KUBE_CONFIG_DATA (base64 kubeconfig), and
variables INGRESS_HOST (real DNS name) and TLS_SECRET (Secret name). Do not
commit these credentials. The source overlays deliberately use .invalid DNS
placeholders, which the release preparation script refuses to deploy.

## Promotion

1. Merge reviewed changes onto the protected branch and wait for successful CI
   and Build and Publish runs on the same SHA.
2. Dispatch the matching environment workflow from its allowed branch with the
   full lowercase 40-character SHA. Promotion does not rebuild images.
3. The gate verifies branch ancestry and latest successful push CI/publisher
   runs. It checks that both GHCR images exist and that namespace/secrets exist.
4. Render configuration and a unique migration Job using the same backend image
   and Secret references. Apply ConfigMap, create the Job, and wait for success.
5. Apply workloads only after migration succeeds; wait for backend and frontend
   rollouts. A failed Job or rollout fails the workflow and needs investigation.
6. Verify HTTPS frontend, /health, /api/health and /api/api/v1/health, plus a
   database-backed application operation. /health is process liveness, not a DB
   readiness check. The live frontend uses the same-origin /api proxy; verify registration, login, search, saved events, consent and logout against the deployed database.

Namespace resources are present in rendered overlays for administrator
provisioning, but the deploy workflow does not apply Namespace objects.
Migration Jobs expire after a day. Failed targets remain inspectable; do not
retry a destructive or incompatible migration blindly. Backward-compatible
migrations and a tested backup are required because old app replicas may run
while migration executes. No automatic database downgrade or rollback occurs.

## Verification and recovery

Read pod events and migration/rollout status in the approved namespace. Avoid
printing Secret objects or full environment dumps. See rollback.md. Image tags
are source SHA identifiers, not registry-enforced immutable digests; restrict
GHCR writes and consider digest attestation before production approval.
This implementation is locally validated but is not certified production-ready.

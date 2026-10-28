# Rollback runbook

## Purpose
This procedure restores an explicitly approved known-good application image after
a failed rollout or health regression. It never restores/downgrades a database.
Use the [DEVOPS-008 safety procedure](rollback-and-disaster-recovery.md) for the
guarded helper, schema compatibility gate and deployed smoke checks.

## Preconditions
- Access to the target Kubernetes cluster.
- Prior deployment history available via `kubectl rollout history`.
- A healthy previous revision exists.

## Procedure
1. Confirm the failed deployment.
2. Identify the currently deployed revision.
3. Review deployment history:
   ```bash
   kubectl --context <approved-context> -n hackathon-prod rollout history deployment/backend
   kubectl --context <approved-context> -n hackathon-prod rollout history deployment/frontend
   ```
4. After confirming schema, configuration and cross-component compatibility,
   select an explicitly reviewed known-good revision (not an arbitrary predecessor):
   ```bash
   kubectl --context <approved-context> -n hackathon-prod rollout undo deployment/backend --to-revision=<approved-backend-revision>
   kubectl --context <approved-context> -n hackathon-prod rollout undo deployment/frontend --to-revision=<approved-frontend-revision>
   ```
5. Wait for rollout completion:
   ```bash
   kubectl --context <approved-context> -n hackathon-prod rollout status deployment/backend --timeout=300s
   kubectl --context <approved-context> -n hackathon-prod rollout status deployment/frontend --timeout=300s
   ```
6. Validate deployed images, /health, /api/health, database-backed catalog, browser
   and authenticated acceptance. /health alone establishes liveness, not DB health.

## Database note
Application rollback is separate from database recovery. Never automatically run
`alembic downgrade` or restore as part of application rollback. The current latest
downgrade drops email_deliveries; the prior downgrade drops revoked_tokens. Require
tested old-application/current-schema compatibility, and a separate approved
recovery plan for actual data incidents. See the linked safety procedure.

## Escalation
Escalate to the incident owner if the application remains unhealthy after rollback or if database changes may have caused data integrity issues.

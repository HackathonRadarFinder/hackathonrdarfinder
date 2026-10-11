# Rollback runbook

## Purpose
This procedure restores the previous known-good deployment after a failed rollout or health regression.

## Preconditions
- Access to the target Kubernetes cluster.
- Prior deployment history available via `kubectl rollout history`.
- A healthy previous revision exists.

## Procedure
1. Confirm the failed deployment.
2. Identify the currently deployed revision.
3. Review deployment history:
   ```bash
   kubectl -n hackathon-prod rollout history deployment/backend
   kubectl -n hackathon-prod rollout history deployment/frontend
   ```
4. Roll back to the previous revision:
   ```bash
   kubectl -n hackathon-prod rollout undo deployment/backend
   kubectl -n hackathon-prod rollout undo deployment/frontend
   ```
5. Wait for rollout completion:
   ```bash
   kubectl -n hackathon-prod rollout status deployment/backend
   kubectl -n hackathon-prod rollout status deployment/frontend
   ```
6. Validate `/health` and frontend availability.

## Database note
Application rollback is separate from database migration safety. Do not assume `alembic downgrade` is safe for production. Prefer backward-compatible migrations and restore from backup only when required.

## Escalation
Escalate to the incident owner if the application remains unhealthy after rollback or if database changes may have caused data integrity issues.

# Incident response

## Purpose
Handle service degradation, failed deploys, and health-check regression in a controlled way.

## Trigger conditions
- Backend `/health` responds with failure.
- Frontend is unavailable or returns errors.
- CrashLoopBackOff or repeated restarts.
- High error rate or database outage.

## Procedure
1. Verify environment and namespace.
2. Check pod health, logs, and deployment status.
3. Check database connectivity and external dependencies.
4. Decide whether to rollback or to fix a configuration issue.
5. Communicate status to the incident owner.

## Recovery
- If deployment is faulty, initiate rollback via the documented recovery steps.
- If the database is unhealthy, restore from backup and validate.

## Escalation
Escalate to the technical owner when the incident affects production or requires a data restore.

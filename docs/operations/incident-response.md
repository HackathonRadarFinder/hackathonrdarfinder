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
- A failed database health check is not proof of corrupted data. Inspect
  connectivity, capacity, credentials configuration, locks and server health
  before choosing recovery. Preserve the existing volume and evidence.
- Restore only when data loss/corruption is established and the incident owner
  approves a concrete recovery plan. Validate the backup in an isolated database
  first, compare the proposed recovery point and schema/application compatibility,
  and use a new target with an explicit cutover plan. Follow
  `database-backup-and-recovery.md`; never overwrite production to investigate an
  outage. Application rollback does not require database restore or downgrade.

## Security incidents
1. Assign an incident owner and record impact, start time and affected functions.
2. Restrict the affected access path or pause the source; preserve logs and
   evidence with authorized access. Do not paste secrets or personal data into
   reports. Isolate suspect source content from extraction/model workflows.
3. Assess suspected disclosure, suspicious privileged access, SSRF or credential
   exposure. Credential rotation and live infrastructure changes require the
   authorized owner's approval; document the scope and session invalidation plan.
4. Notify the designated security/platform owner and affected parties under the
   approved incident policy. Record decisions, containment and recovery actions.
5. Validate safe recovery, review root cause and corrective controls, and close
   with an evidence-backed review. This procedure still requires a tabletop and
   target-environment exercise before SEC-12 acceptance.

## Escalation
Escalate to the technical owner when the incident affects production or requires a data restore.

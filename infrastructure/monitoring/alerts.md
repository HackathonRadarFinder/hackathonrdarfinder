# Alerts

## Backend unavailable
- Condition: backend health check fails across replicas for 5 minutes.
- Severity: critical
- Response: validate deployment, inspect logs, verify DB connectivity.
- Escalation: incident owner, platform team.

## High 5xx rate
- Condition: 5xx rate exceeds 10% for 10 minutes.
- Severity: high
- Response: inspect application logs and deployment rollout history.
- Escalation: application owner.

## CrashLoopBackOff
- Condition: pod restarts exceed 3 in 10 minutes.
- Severity: high
- Response: inspect restart count, events, and resource limits.

## High CPU or memory
- Condition: average CPU > 85% or memory > 85% for 10 minutes.
- Severity: medium
- Response: inspect HPA and scaling configuration.

## Database unavailable
- Condition: PostgreSQL readiness fails or connection count is zero.
- Severity: critical
- Response: validate database host, credentials, and storage health.

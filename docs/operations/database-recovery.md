# Database recovery

## Purpose
Document the operational steps for PostgreSQL recovery after a data problem or partial outage.

## Preconditions
- A valid, recent backup is available.
- Database credentials and a restore target are available.
- The application is placed into maintenance mode if needed.

## Procedure
1. Assess the extent of the issue.
2. Confirm whether the application or database is the primary outage cause.
3. Restore the latest valid backup to a non-production test database first.
4. Validate the restored database.
5. Promote the restored database only after validation passes.

## Recovery time objective
This repository assumes an initial RTO target of 4 hours and an RPO target of 15 minutes unless a business requirement changes these values.

## Escalation
Escalate to the database owner or incident commander before any production restore that might overwrite live data.

# Hackathon Radar: Deployment Rollback & Disaster Recovery Procedure

## 1. Overview & Objectives
This document establishes the official rollback and disaster recovery (DR) procedures for **Hackathon Radar**. The objective is to rapidly restore service availability, guarantee data consistency, and minimize downtime in the event of failed deployments, broken migrations, critical security vulnerabilities, or major infrastructure outages.

### Recovery Objectives
- **Target Rollback Execution SLA**: $\le 5\text{ minutes}$ from decision to restored traffic.
- **Recovery Time Objective (RTO)**: $\le 30\text{ minutes}$ for complete disaster recovery.
- **Recovery Point Objective (RPO)**: $\le 15\text{ minutes}$ maximum acceptable data loss.

---

## 2. Rollback Triggers & Decision Criteria

A rollback must be initiated immediately if any of the following triggers are observed post-deployment:
1. **Critical API Degradation**: HTTP 5xx error rate $> 1\%$ for $> 3$ consecutive minutes.
2. **Frontend Unavailability**: Homepage or radar app fails to render or crashes with unhandled runtime exceptions.
3. **Database Migration Failure**: Migration scripts fail midway, table locks cause cascading connection exhaustion, or critical data is corrupted.
4. **Authentication Failure**: Users unable to sign in, sessions prematurely invalidated, or security token generation failing.
5. **Prediction Engine Failure**: AI recommendation engine throwing 500 errors or latency $P95 > 2000\text{ms}$.
6. **Worker / Scraper Crash Loop**: Workers repeatedly OOMKilled or unable to connect to messaging brokers.

---

## 3. Rollback Procedure by Component

```
Deployment Released ───► Smoke Verification ───► Degradation Detected
                                                        │
         ┌──────────────────────────────────────────────┘
         ▼
Trigger Rollback Decision (Release Commander)
         │
         ├───► 1. Frontend: Revert CDN / Roll back Nginx container
         ├───► 2. Backend: Revert K8s Deployment to previous Docker tag
         ├───► 3. Database: Check migration state -> Execute down-revision SQL
         └───► 4. Workers: Restart with verified image tag & reset queues
         │
         ▼
Post-Rollback Validation (Health, Smoke Tests, Log Telemetry)
         │
         ▼
Service Restored ───► Post-Mortem Incident Report Logged
```

### 3.1 Frontend Rollback
#### Kubernetes / Containerized Deployments
```bash
# Revert to previous deployment revision
kubectl rollout undo deployment/hackathon-radar-frontend -n production

# Monitor rollout progression
kubectl rollout status deployment/hackathon-radar-frontend -n production --timeout=120s
```

#### Static Hosting / CDN Deployments
- Invalidate CloudFront / Cloudflare cache for index and asset bundles:
  ```bash
  aws cloudfront create-invalidation --distribution-id $CDN_DIST_ID --paths "/*"
  ```
- Re-point DNS / router to previous release S3 / artifact bucket.

---

### 3.2 Backend Rollback
#### Kubernetes Deployment Rollback
```bash
# Identify previous stable revision
kubectl rollout history deployment/hackathon-radar-backend -n production

# Roll back to immediate predecessor revision
kubectl rollout undo deployment/hackathon-radar-backend -n production

# Or roll back to specific image tag:
kubectl set image deployment/hackathon-radar-backend \
  backend=ghcr.io/hackathonradarfinder/backend:v1.0.0 -n production
```

#### Docker Compose Rollback
```bash
# Switch environment tag in .env
sed -i 's/BACKEND_IMAGE_TAG=.*/BACKEND_IMAGE_TAG=v1.0.0/' .env
docker compose up -d backend
```

---

### 3.3 Database Migration Rollback
> [!CAUTION]
> Always verify whether the newly introduced schema changes are backward-compatible before reverting code. In an **expand-and-contract** pattern, rolling back application code without rolling back database schema is often safe.

If database schema downgrade is strictly necessary:
1. Put the application in maintenance mode if locks are required.
2. Check current migration revision:
   ```bash
   alembic current
   ```
3. Revert to target stable revision:
   ```bash
   alembic downgrade -1
   # Or target explicit revision ID:
   alembic downgrade <target_revision_id>
   ```
4. If migrations were non-reversible, execute pre-release point-in-time recovery (PITR) snapshot restore.

---

### 3.4 Scraper Workers & Queue Recovery
If background ingestion workers fail:
1. Stop running worker pods:
   ```bash
   kubectl scale deployment/hackathon-radar-workers --replicas=0 -n production
   ```
2. Flush or inspect poisoned messages from Redis:
   ```bash
   redis-cli -u $REDIS_URL LLEN scraper_dead_letter_queue
   ```
3. Roll back worker image tag to previous stable build.
4. Scale workers back up:
   ```bash
   kubectl scale deployment/hackathon-radar-workers --replicas=3 -n production
   ```

---

## 4. Disaster Recovery (DR) Scenarios & Runbooks

### Scenario 1: Primary Database Outage / Storage Corruption
1. **Diagnosis**: Database connection timeout alerts; pods reporting `OperationalError: could not connect to server`.
2. **Action Plan**:
   - Check status on cloud managed database (AWS RDS / Cloud SQL).
   - If instance is unreachable, initiate failover to standby replica (Multi-AZ failover).
   - If data corruption occurred, initiate Point-in-Time Recovery (PITR) to a timestamp 5 minutes prior to corruption.
   - Update `DATABASE_URL` secret and restart backend pods.

### Scenario 2: Corrupted Deployment / Fatal Config Error
1. **Diagnosis**: Pods stuck in `CrashLoopBackOff` or immediate `502 Bad Gateway` after release.
2. **Action Plan**:
   - Execute `./scripts/rollback-deployment.sh --env=production`.
   - Inspect secrets and environment variable values for missing keys or malformed URIs.
   - Confirm healthy status with `./scripts/verify-post-rollback.sh`.

### Scenario 3: Accidental Data Deletion or Ingestion Cascade
1. **Diagnosis**: Admin or scraper accidentally purges verified hackathon records.
2. **Action Plan**:
   - Immediately pause scrapers: `kubectl scale deployment/scraper-workers --replicas=0`.
   - Restore affected tables from latest automated daily backup into an isolated staging schema:
     ```bash
     pg_restore -d hackathonradar_recovery backup_latest.dump --table=events --table=organizations
     ```
   - Run reconciliation script to copy missing records back to primary database.

---

## 5. Post-Rollback Validation Checklist

Immediately after rollback execution, verify:
- [ ] **HTTP Health Probe**: `GET /health` returns `HTTP 200 OK`.
- [ ] **Version Stamp**: `GET /version` reports the rollback version tag and commit SHA.
- [ ] **Frontend Accessibility**: Homepage, World Map Radar, and navigation render without console errors.
- [ ] **Database Connectivity**: Event listings load and user bookmark queries execute within $< 150\text{ms}$.
- [ ] **Authentication**: User login and session restoration function properly.
- [ ] **Prediction Engine**: Skill match score calculation runs cleanly.
- [ ] **Background Workers**: Queue depths decrease; no unhandled exception loops in logs.
- [ ] **Telemetry Stability**: Error rate $< 0.05\%$, CPU and memory utilization within baseline limits.

---

## 6. Incident Reporting Template

For every production rollback or emergency recovery event, complete the following incident log within 24 hours:

```markdown
# Incident Report: INC-[YEAR]-[NUMBER]

- **Incident Date / Time (UTC):** YYYY-MM-DD HH:MM
- **Severity Level:** P0 (Critical Outage) / P1 (Major Degradation)
- **Affected Environment:** Production
- **Failed Release Version:** vX.Y.Z (Commit SHA: _______)
- **Rollback Target Version:** vX.Y.(Z-1) (Commit SHA: _______)
- **Time to Detect (TTD):** ___ minutes
- **Time to Recover (TTR):** ___ minutes

## 1. Incident Summary
Brief narrative of what occurred, symptoms detected, and user impact.

## 2. Root Cause Analysis (RCA)
Detailed technical explanation of why the failure happened.

## 3. Rollback & Recovery Actions Taken
Chronological log of mitigation steps executed.

## 4. Preventive Actions & Follow-up Tickets
- [ ] Action item 1 (Issue #___)
- [ ] Action item 2 (Issue #___)
```

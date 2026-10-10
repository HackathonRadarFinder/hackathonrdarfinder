# Hackathon Radar: Production Readiness Checklist

This checklist serves as the final quality and operational gate before releasing any version of **Hackathon Radar** to production. Every item must be verified, signed off, and archived in the release pull request or release issue.

---

## Release Metadata
- **Release Version:** `v__________________`
- **Target Git Commit SHA:** `________________________________________`
- **Target Release Date / Time:** `YYYY-MM-DD HH:MM UTC`
- **Release Commander:** `@__________________`
- **Tech Lead Sign-off:** `@__________________`
- **DevOps / SRE Sign-off:** `@__________________`
- **QA Lead Sign-off:** `@__________________`

---

## Gate 1: Code Quality, Build & CI/CD Status
- [ ] All pull requests merged into `main` or release branch have passed required code reviews (min 2 reviewers).
- [ ] GitHub Actions CI pipeline is 100% green on target Git commit:
  - [ ] Linting and formatting checks (`eslint`, `flake8`/`black`) pass with zero errors.
  - [ ] Frontend production build (`npm run build`) completes successfully.
  - [ ] Backend test suites (`pytest`, `unittest`) execute with 100% pass rate.
  - [ ] Docker container images build cleanly with multi-stage caching and non-root execution.
- [ ] No temporary debug code, `console.log` floods, or mock bypass switches left in production code paths.
- [ ] Git commit history is clean and rebased/squashed appropriately.

---

## Gate 2: Regression, Integration & E2E Testing
- [ ] Full regression test suite passed in staging environment matching production topology.
- [ ] Core end-to-end user journeys verified:
  - [ ] User landing, search query execution, and category filtering.
  - [ ] Global radar interactive map loading, projection resets, and marker interactions.
  - [ ] User authentication, profile preference setting, and AI match scoring.
  - [ ] Hackathon bookmarking and calendar export flows.
  - [ ] Admin operations: review queue, scraper health, duplicate resolution.
- [ ] Zero open P0 (Blocker) or P1 (Critical) defects.
- [ ] Any accepted P2/P3 defects documented with known workarounds and tracked in backlog.

---

## Gate 3: Security & Compliance Validation
- [ ] Dependency vulnerability audit executed:
  - [ ] `npm audit --omit=dev` reports 0 Critical and 0 High vulnerabilities.
  - [ ] `pip-audit` or safety scan reports 0 unpatched critical CVEs.
- [ ] Automated secret scanning passed (no API keys, database credentials, or private certificates committed).
- [ ] OWASP Top 10 security review:
  - [ ] Input sanitization on all search, filter, and submission endpoints.
  - [ ] CORS headers configured strictly for allowed production origins.
  - [ ] Content Security Policy (CSP), HSTS, and X-Frame-Options headers enabled.
  - [ ] Authentication session tokens use `Secure`, `HttpOnly`, and `SameSite=Strict` flags.
- [ ] Role-Based Access Control (RBAC) verified for `/admin/*` routes (least-privilege enforcement).

---

## Gate 4: Database Migrations & Data Integrity
- [ ] Database schema migrations tested in staging with production-scale data snapshot.
- [ ] Migrations adhere to the **Expand and Contract (zero downtime)** pattern:
  - [ ] New columns added with default values or nullable.
  - [ ] No destructive `DROP TABLE` or `DROP COLUMN` in phase 1.
- [ ] Migration execution time estimated (locks analyzed; long-running operations batched).
- [ ] Corresponding automated rollback SQL scripts tested and verified:
  - [ ] Rollback migration reverts schema without unrecoverable data loss.
- [ ] Database connection pool limits validated against production connection limits.

---

## Gate 5: Configuration & Secrets Management
- [ ] Production environment variables verified against `.env.example`.
- [ ] All production secrets injected securely via Secret Manager / Vault / GitHub Secrets:
  - [ ] Database credentials, Redis URLs, external API keys (scrapers, LLM providers).
- [ ] Zero hardcoded credentials or staging endpoints remaining in production config.
- [ ] TLS certificates verified for domain and API gateways (expiration > 30 days).
- [ ] DNS records, CDN routes, and SSL termination points validated.

---

## Gate 6: Infrastructure, Resource Capacity & Scalability
- [ ] Container resource limits defined:
  - [ ] Frontend container: CPU request `100m` / limit `500m`, Memory request `128Mi` / limit `512Mi`.
  - [ ] Backend container: CPU request `250m` / limit `1000m`, Memory request `512Mi` / limit `2Gi`.
- [ ] Horizontal Pod Autoscaler (HPA) configured:
  - [ ] Min replicas: 2 (high availability across availability zones).
  - [ ] Max replicas: 10, scaling on CPU > 70% or memory > 80%.
- [ ] Cloud provider quota limits checked (compute, ingress bandwidth, database IOPS).
- [ ] CDN caching rules active for static assets with immutable cache-control headers.

---

## Gate 7: Database Backup & Point-in-Time Recovery
- [ ] Fresh automated database snapshot created immediately prior to release execution.
- [ ] Backup integrity and restore capability verified:
  - [ ] Point-in-time recovery (PITR) enabled with RPO $\le$ 15 minutes.
  - [ ] Restore procedure documented with RTO $\le$ 30 minutes.
- [ ] Storage volume snapshots captured for stateful services if applicable.

---

## Gate 8: Observability, Monitoring & Alerting
- [ ] Health check probes active and responding:
  - [ ] Liveness probe: `/health/liveness` returns HTTP 200 within 200ms.
  - [ ] Readiness probe: `/health/readiness` verifies database and cache connectivity.
- [ ] Prometheus metrics exported for request throughput, error rates, and p99 latency.
- [ ] Centralized logging active (structured JSON format with correlation IDs / trace IDs).
- [ ] Critical alert channels tested and routed to on-call duty:
  - [ ] HTTP 5xx error rate > 1% over 5 minutes.
  - [ ] API latency p95 > 500ms over 5 minutes.
  - [ ] Database CPU > 85% or available disk space < 15%.
  - [ ] Scraper failure rate > 10% on scheduled ingestion runs.

---

## Gate 9: Rollback Strategy & Readiness
- [ ] Rollback strategy defined and documented:
  - [ ] Strategy type: **Canary / Blue-Green / Rolling Rollback**.
  - [ ] Target Rollback SLA: $\le$ 5 minutes from decision.
- [ ] Rollback command validated in staging:
  ```bash
  # Kubernetes deployment rollback
  kubectl rollout undo deployment/hackathon-radar-frontend -n production
  kubectl rollout undo deployment/hackathon-radar-backend -n production
  ```
- [ ] Data rollback plan in place in case database migrations occurred.
- [ ] Clear rollback abort criteria agreed upon (e.g., error rate > 0.5% for > 3 minutes).

---

## Gate 10: Smoke Testing Protocol
Immediately upon deployment, execute automated & manual smoke tests:
- [ ] **ST-01:** Health check `/health` returns `HTTP 200 OK` with correct version and commit SHA.
- [ ] **ST-02:** Homepage loads within 1.5 seconds on desktop and mobile.
- [ ] **ST-03:** Live Radar map renders global hubs and responds to zoom/filter interactions.
- [ ] **ST-04:** Opportunity search returns verified hackathons with active prizes.
- [ ] **ST-05:** AI prediction scoring dynamically calculates match percentage for user skills.
- [ ] **ST-06:** Scraper collector trigger endpoint initiates ingestion without uncaught exceptions.
- [ ] **ST-07:** Admin review dashboard loads without authentication bypass or permission errors.

---

## Gate 11: Release Approval & Sign-Off Documentation
All designated release roles must supply explicit sign-off before production traffic is shifted:

| Role | Name | Status | Timestamp (UTC) | Signature / Note |
| :--- | :--- | :--- | :--- | :--- |
| **Release Commander** | | [ ] Approved [ ] Rejected | | |
| **Tech Lead** | | [ ] Approved [ ] Rejected | | |
| **DevOps / SRE** | | [ ] Approved [ ] Rejected | | |
| **QA Lead** | | [ ] Approved [ ] Rejected | | |

---

## Gate 12: Post-Deployment Soak Period & Telemetry
Following full traffic cutover, observe system stability for **60 minutes**:
- [ ] **Telemetry Check (T+15m):**
  - Error rate: `< 0.05%` (Actual: `_____ %`)
  - P95 Latency: `< 250ms` (Actual: `_____ ms`)
  - CPU / Memory utilization normal across all pods.
- [ ] **Telemetry Check (T+30m):**
  - User traffic patterns stable.
  - Zero critical P0/P1 alerts triggered.
- [ ] **Telemetry Check (T+60m):**
  - Soak period complete with zero regressions.
  - Release Commander updates release ticket to **DEPLOYED & STABLE**.
  - Notify stakeholders via Slack `#announcements` / `#engineering-releases`.

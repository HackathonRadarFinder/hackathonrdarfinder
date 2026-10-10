# Hackathon Radar: Release Management Policy

## 1. Purpose & Scope
This policy establishes a standardized, repeatable, and auditable release management process for the **Hackathon Radar** platform. The goal is to ensure all production deployments are validated against formal quality, security, operational, and rollback criteria, preventing regressions, outages, and data inconsistencies.

This policy applies to all components of Hackathon Radar:
- Frontend Web Application (React / Vite)
- Backend APIs & Microservices (Python / FastAPI / Node.js)
- Scrapers & Ingestion Collectors (Dynamic and Static Collectors)
- Data Pipelines, ML Models, and Database Migrations
- Infrastructure and Deployment Configurations (Docker, Kubernetes, CI/CD)

---

## 2. Release Versioning Strategy

Hackathon Radar strictly adheres to **Semantic Versioning 2.0.0 (SemVer)**:

$$\text{v}\mathbf{MAJOR}.\mathbf{MINOR}.\mathbf{PATCH}[-\mathbf{PRERELEASE}]$$

### 2.1 Version Numbering Rules
1. **MAJOR (X.0.0)**: Incremented when making incompatible API changes, major architectural migrations, breaking database schema transformations, or redesigning core authentication flows.
2. **MINOR (0.Y.0)**: Incremented when adding functionality in a backward-compatible manner (e.g., new scraper sources, new admin dashboard views, new AI prediction filters).
3. **PATCH (0.0.Z)**: Incremented when applying backward-compatible bug fixes, security patches, or minor configuration updates.
4. **Pre-release (`-rc.N`, `-beta.N`)**: Used for staging validation candidates prior to production promotion (e.g., `v1.2.0-rc.1`).

### 2.2 Git Tagging Convention
Every production release must be tagged from the merge commit on the `main` branch:
- Format: `vX.Y.Z` (e.g., `v1.0.0`)
- Annotated Tag with signed cryptographic signature:
  ```bash
  git tag -a v1.0.0 -m "Release v1.0.0: Hackathon Radar Production Launch"
  git push origin v1.0.0
  ```

---

## 3. Branching and Release Workflow

Hackathon Radar follows a structured Git flow for all releases:

```
feature/*  ───►  main (via PR + CI)  ───►  release/vX.Y.Z (RC branch)  ───►  Production (Tagged vX.Y.Z)
                                                                                  │
hotfix/*   ───────────────────────────────────────────────────────────────────────┘
```

### 3.1 Environments & Promotion Path
| Environment | Branch / Source | Purpose | Deploy Trigger |
| :--- | :--- | :--- | :--- |
| **Development (`dev`)** | `feature/*` / PR branches | Local & preview developer validation | Automated on PR commit |
| **Staging (`stage`)** | `main` | Production-identical rehearsal, integration & E2E tests | Automated on merge to `main` |
| **Release Candidate (`rc`)** | `release/vX.Y.Z` | Production readiness audit, smoke test, CAB sign-off | Tag / manual workflow trigger |
| **Production (`prod`)** | Tagged release `vX.Y.Z` | Customer-facing live traffic | Automated post CAB approval |

### 3.2 Hotfix Flow
Emergency patches for critical production defects (P0/P1 incidents):
1. Branch created directly from the deployed production tag: `hotfix/vX.Y.(Z+1)`.
2. Minimal isolated fix applied with dedicated regression test.
3. Fast-tracked through expedited security & smoke test checklist.
4. Deployed to production and tagged as `vX.Y.(Z+1)`.
5. Backported immediately into `main` to prevent regression.

---

## 4. Release Roles & RACI Matrix

| Role | Primary Responsibilities | RACI Mapping |
| :--- | :--- | :--- |
| **Release Commander** | Orchestrates release lifecycle, chairs Go/No-Go decision, coordinates communications. | **Accountable (A)** |
| **Tech Lead** | Validates technical architecture, approves database migrations, reviews code diff. | **Responsible (R)** |
| **DevOps / SRE Engineer** | Executes deployment, validates infrastructure readiness, executes rollback if needed. | **Responsible (R)** |
| **QA Lead** | Validates test pass rate, runs smoke suite, confirms zero blocker bugs. | **Responsible (R)** |
| **Security Lead** | Reviews dependency CVEs, secret scans, and access permissions. | **Consulted (C)** |
| **Product Owner** | Confirms feature scope, signs off user-facing changes and release notes. | **Informed (I)** |

---

## 5. Release Approval Requirements & Gates

A release is approved for production deployment **only when all gates pass**:

1. **Automated CI Gate**: All GitHub Actions workflows (unit tests, integration tests, lint, TypeScript/Python type checks, container builds) must be 100% green.
2. **Security Gate**: Zero high or critical unpatched CVEs in dependency audits (`npm audit`, `pip-audit`), clean secret scan reports.
3. **Database Migration Gate**: Schema migrations must be backward-compatible (expand-contract pattern) with tested rollback SQL scripts.
4. **Two-Person Rule**: Deployment requires dual approvals in GitHub Environments (Release Commander + Tech Lead).
5. **Signed Production Readiness Checklist**: Fully executed checklist recorded in GitHub PR or Release Issue.

---

## 6. Release Windows & Scheduling

### 6.1 Standard Release Window
- **Days**: Tuesday to Thursday.
- **Hours**: 10:00 AM – 2:00 PM UTC (low-traffic periods, ensuring full engineering team availability).
- **Friday Releases**: Strictly prohibited except for P0 security hotfixes.

### 6.2 Release Blackout Periods
Releases are frozen during:
- Major live hackathons and peak competition submission deadlines.
- Critical national/global holidays with reduced engineering on-call coverage.
- Ongoing unresolved P0/P1 system incidents.

---

## 7. Version & Git Commit Recording

Every deployed build must capture its deployment provenance:
- **Git Commit SHA**: Injected at build time via `VITE_GIT_COMMIT_SHA` / `GIT_COMMIT_SHA`.
- **Release Version**: Tagged version injected via `APP_VERSION`.
- **Build Timestamp**: ISO-8601 timestamp injected via `BUILD_TIMESTAMP`.
- **Health / Version Endpoints**:
  - Backend: `GET /health` and `GET /version` returning JSON payload:
    ```json
    {
      "status": "healthy",
      "version": "1.0.0",
      "commit": "a4d3e4c",
      "environment": "production",
      "timestamp": "2026-10-10T12:00:00Z"
    }
    ```
  - Frontend: Console banner and `window.__APP_VERSION__` metadata.

---

## 8. Post-Deployment Validation & Soak Period

Following deployment to production:
1. **Immediate Smoke Test (0 – 10 mins)**: Verify core user journeys:
   - Homepage and Global Radar load without console errors.
   - Search & filtering returns active hackathons.
   - User authentication and bookmarking workflows function.
   - Admin review console and scrapers report normal telemetry.
2. **Active Soak Window (10 – 60 mins)**:
   - Monitor real-time error rates (target: `< 0.05%` HTTP 5xx).
   - Monitor API response latency (target: p95 `< 250ms`, p99 `< 500ms`).
   - Monitor infrastructure CPU and memory saturation (target: `< 70%`).
3. **Release Sign-Off**: Release Commander marks release as complete in GitHub and closes corresponding release ticket.

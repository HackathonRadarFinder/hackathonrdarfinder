# Hackathon Radar AI

**Hackathon Radar AI** is an intelligent hackathon discovery, tracking, and prediction platform. It combines real-time global event tracking, automated source ingestion, personalized AI skill matching, and an operations suite for administrators.

---

## 🧭 Key Platform Features

- **Global Innovation Radar**: Interactive geospatial command center tracking hackathon hubs worldwide.
- **Live Opportunity Engine**: Filter competitions by prize pool, modality (Remote, Hybrid, In-Person), and deadline countdown.
- **Personalized AI Predictions**: Skill-based matching for developers and builders with clear match reasoning.
- **10-View Admin Operations**: Review queues, scraper ingestion telemetry, duplicate resolution, and feature flags.
- **Compliance Collector Engine (v2.2)**: Automated web scrapers with strict rate limiting and robots.txt compliance.

---

## 🛠️ Quick Start

### Prerequisites
- Node.js 18+ LTS
- Python 3.10+ (for backend collector engine)

### Run Frontend Locally
```bash
# 1. Install dependencies
npm install

# 2. Start Vite development server
npm run dev

# 3. Build production bundle
npm run build
```

---

## 🚀 DevOps & Production Readiness

Hackathon Radar enforces a formal release management and production readiness process:

- **[Release Management Policy](docs/devops/release-management-policy.md)**: Semantic Versioning (SemVer 2.0.0), branching strategy, RACI matrix, and deployment gates.
- **[Production Readiness Checklist](docs/devops/production-readiness-checklist.md)**: 12-Gate verification covering CI/CD, testing, security audits, database migrations, monitoring, and rollback readiness.
- **[Release Notes Template](docs/devops/release-notes-template.md)**: Standardized template for communicating production releases.
- **[Changelog](CHANGELOG.md)**: Complete changelog tracking all released and unreleased milestones.

### Verify Release Readiness
Run the automated verification script prior to creating a release pull request:
```bash
./scripts/verify-release-readiness.sh
```

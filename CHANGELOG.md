# Changelog

All notable changes to the **Hackathon Radar** platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- **DevOps Release Management & Production Readiness Suite ([#55](https://github.com/HackathonRadarFinder/hackathonrdarfinder/issues/55))**:
  - Formal Release Management Policy (`docs/devops/release-management-policy.md`) covering SemVer, Git flow, branching strategy, RACI matrix, and approval gates.
  - Comprehensive 12-Gate Production Readiness Checklist (`docs/devops/production-readiness-checklist.md`).
  - Standardized Release Notes Template (`docs/devops/release-notes-template.md`).
  - GitHub Pull Request template for release gates (`.github/PULL_REQUEST_TEMPLATE/release_readiness.md`).
  - GitHub Issue template for production release candidates (`.github/ISSUE_TEMPLATE/production_release.md`).
  - Automated executable release readiness verification script (`scripts/verify-release-readiness.sh`).
  - Continuous release gate validation workflow (`.github/workflows/release-readiness-gate.yml`).

---

## [1.0.0] - 2026-10-10

### Added
- **Global Hackathon Radar**: Interactive command-center world map showcasing global innovation epicenters (San Francisco, Seattle, New York, London, Geneva, Mumbai, Bengaluru, Singapore, Tokyo).
- **Opportunity Discovery Engine**: Real-time filtering by category, modality (Remote, Hybrid, In-Person), prize pool, and registration deadline.
- **Personalized AI Predictions**: Skill-based recommendation engine matching builder profiles with verified competitions.
- **Admin Operations Suite**: Full moderation suite including review queues, source management, scraper health, data quality flags, and feature configuration.
- **Collector Engine (v2.2)**: Automated web scrapers with compliance checking, robots.txt verification, and storage backends.

# Hackathon Radar Finder — MVP Release Checklist

Target date: October 18, 2026
Integration branch: develop
Production release branch: main

## 1. Code and CI
- [ ] All approved integration PRs merged into develop
- [ ] Release commit reviewed before promotion to main
- [ ] Backend and collector tests pass
- [ ] Frontend build, lint and tests pass
- [ ] Infrastructure checks and Docker builds pass
- [ ] Published images match the approved full commit SHA

## 2. Database
- [ ] PostgreSQL 16 connectivity verified
- [ ] Alembic migrations tested on staging
- [ ] Durable backup configured and verified
- [ ] Backup restoration tested on disposable PostgreSQL
- [ ] Migration compatibility reviewed before deployment

## 3. Application
- [ ] Registration and login verified in browser
- [ ] Real hackathon catalog loads
- [ ] Search, filters and pagination work
- [ ] Event details and predictions work
- [ ] Saved events and reminder consent work
- [ ] Admin access restrictions verified

## 4. Operations
- [ ] Environment secrets configured securely
- [ ] DNS and HTTPS verified
- [ ] Application health checks pass
- [ ] Scheduled collection verified
- [ ] Email delivery tested using an authorized destination
- [ ] Application rollback rehearsed on staging

## 5. Release Acceptance
- [ ] Production environment approval received
- [ ] No unresolved release-blocking defects
- [ ] Production deployment successful
- [ ] Post-deployment smoke tests passed
- [ ] Logs and application health monitored
- [ ] Release owner approves final handover

## Release Decision

Status: NOT YET APPROVED

Passing automated tests does not establish production readiness.
Database recovery, browser acceptance, environment provisioning
and production deployment require separate verification.

Record the release SHA, approval evidence, deployment URL,
known limitations and test results before final sign-off.

---
name: Production Release Candidate
about: Track a production release through the formal production readiness gate
title: "[RELEASE] Production Release vX.Y.Z"
labels: ["release", "production-readiness"]
assignees: []
---

## 🚀 Release Information
- **Release Version:** `v`
- **Target Release Date:** `YYYY-MM-DD`
- **Deployment Window:** `10:00 - 14:00 UTC`
- **Release Commander:** @
- **Tech Lead:** @
- **DevOps / SRE:** @
- **QA Lead:** @

---

## 📋 Release Phases & Readiness Checklist

### Phase 1: Pre-Release Validation (Staging)
- [ ] Staging deployment completed and stable
- [ ] Automated regression suite passed 100%
- [ ] End-to-end user journeys verified
- [ ] Dependency security audit completed (0 High/Critical CVEs)
- [ ] Pre-release database backup snapshot verified
- [ ] Rollback procedures tested and verified

### Phase 2: Dual Approval & Gate Sign-off
- [ ] Production Readiness Checklist signed off by Release Commander
- [ ] Production Readiness Checklist signed off by Tech Lead
- [ ] Deployment ticket approved by Change Advisory Board (CAB)

### Phase 3: Production Rollout
- [ ] Production traffic deployment initiated (Canary / Rolling)
- [ ] Container pods successfully started and health checks passing
- [ ] Post-deployment smoke tests completed successfully

### Phase 4: Post-Release Soak & Closeout
- [ ] 60-minute soak period telemetry verified (Error rate < 0.05%, P95 < 250ms)
- [ ] Git tag `vX.Y.Z` created and pushed to repository
- [ ] Release notes published
- [ ] Stakeholders notified in `#announcements`

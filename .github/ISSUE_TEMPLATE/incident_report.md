---
name: Incident Post-Mortem Report
about: Document a production incident, rollback, or disaster recovery event
title: "[INCIDENT] YYYY-MM-DD: Description of Incident"
labels: ["incident", "post-mortem", "reliability"]
assignees: []
---

## 🚨 Incident Metadata
- **Incident Date / Time (UTC):** `YYYY-MM-DD HH:MM`
- **Severity Level:** P0 (Critical Outage) / P1 (Major Degradation) / P2 (Moderate Impact)
- **Affected Environment:** Production / Staging
- **Failed Release Version:** `vX.Y.Z` (Git SHA: `________`)
- **Rollback Target Version:** `vX.Y.Z` (Git SHA: `________`)
- **Incident Commander:** @
- **Time to Detect (TTD):** `___ minutes`
- **Time to Recover (TTR):** `___ minutes`

---

## 1. Executive Summary
*High-level description of what happened, customer/user impact, and resolution.*

---

## 2. Timeline of Events (UTC)
- `HH:MM` - Deployment completed.
- `HH:MM` - Anomaly / alerts detected.
- `HH:MM` - Rollback decision made by Incident Commander.
- `HH:MM` - Rollback command executed.
- `HH:MM` - Traffic restored and post-rollback smoke tests verified.

---

## 3. Root Cause Analysis (RCA)
*Detailed technical breakdown of the underlying defect or failure mechanism.*

---

## 4. Rollback & Recovery Actions Taken
*Chronological log of remediation steps, database actions, or configuration updates.*

---

## 5. Preventative Action Items
- [ ] Action Item 1 (Owner: @____, Issue: #____)
- [ ] Action Item 2 (Owner: @____, Issue: #____)

## Evidence and safety
Record approved cluster/namespace, release image SHA, schema compatibility decision, rollout result and deployed smoke results. Attach only redacted evidence; never include credentials, Secret values or full environment dumps. Application rollback and any separately approved database recovery must have separate timelines.

# Release checkpoint ? resumed 27 October 2026

Work exclusively in `.release-local`, branch `release/2026-10-28-integration`.

## Current verified result

- Full backend: **484 passed, 12 skipped**. All 12 gated PostgreSQL tests separately executed and passed; built-image browser acceptance passed.
- Targeted backend:114 passed (overlaps full run). Module2.4:33 passed. Operations:67 passed. Workflow/overlay validation and actionlint passed; optional ShellCheck unavailable.
- Complete isolated PostgreSQL journey verifies source registration ? upload ? repeat idempotency ? review ? publication ? explicit duplicate merge ? preserved saved items ? reimport, plus role denials, private preferences, recommendations, scheduled in-app notices, read ownership, email consent/dry-run, ML suppression and logout revocation.
- Existing Docker images reused. No rebuild, persistent application database write, university import, email transmission or public deployment during this resumed run.
- Prior local persistence counts/evidence retained:5 events,3 users,3 saved items,1362 institutions across33 states/UTs. They were not reimported or reaudited.
- PR95 is merged into develop; its two file changes were already present with newer release repairs. PR92 remains a draft. No missing Module2.4 source change required copying.
- Commit `0472b4d` adds PostgreSQL/browser CI gating and portable browser discovery. Release branch remains local/unpushed; remote CI has not executed.
- All15 pre-existing untracked files preserved with unchanged hashes. Accidental root output/lockfile and caches excluded. Separate scraper directory remains unstaged.

## Exact next acceptance action

A real human reviewer must check the supplied Brabble pilot against its source facts and add an explicit, dated approval bound to those exact facts. The single approved schema row is AI-reviewed and currently has **zero human approvals**. Do not reinterpret an operator name or this execution as human review.

A pending, deliberately invalid template is at `docs/release-evidence/2026-10-27-resume/pending-human-approval-template.json`. Its decision remains pending and reviewer fields blank. The Brabble API reference currently permits row reuse with visible credit and organizer links: https://brabble.ai/docs. This does not authorize direct Devfolio/Unstop scraping.

After an actual human completes review, preserve the original acquisition evidence and provider credit in `acquisition_evidence.human_approval`. Use the existing reviewed API import workflow; do not strip provider evidence to force this CSV through the generic upload parser. Validate first without `--apply`; use `--check-target` before an authorized application to the exact development database. Never invent a reviewer or bypass the gate.

For other approved generic datasets, React Admin ? Sources ? upload CSV/XLSX with the exact current approval reference ? review/publish ? duplicate review. The complete workflow has passed on isolated, clearly synthetic fixtures.

Other remaining external inputs:verified historical outcomes for temporal folds/calibration; authorized SMTP test credentials/recipients if email is required; production infrastructure and deployment authorization. These integrations remain disabled or report insufficient readiness.

## Reproduce only affected acceptance

```powershell
Set-Location C:/Users/nakul/OneDrive/Documents/Desktop/hackathonradarfinder/.release-local
backend/.venv/Scripts/python.exe scripts/postgres_acceptance.py --backend-image hackathonradarfinder-backend:local --frontend-image hackathonradarfinder-frontend --out .test-support/new-acceptance
Set-Location backend
.venv/Scripts/python.exe -m workers.evaluate_predictions --neural --output ../.test-support/new-ml-evaluation.json
.venv/Scripts/python.exe -m workers.import_reviewed_public radar_collector/output/brabble-pilot/reviewed.csv
```

Use new output paths. Evaluation uses the actual execution clock; it rejects future evidence cutoffs. The explicit 27 October cutoff was rejected when ahead of the host clock; the successful recorded evaluation used its actual clock and remained insufficient_history.

Latest evidence:`docs/release-evidence/2026-10-27-resume/`. Raw results:`.test-support/release-resume-20261027/`. See `FINAL_RELEASE_REPORT.md` for full scope and previous browser/persistence results. Keep backend/.env and .local-backups private; do not reset volumes. No remote push or PR submission is claimed.

# Release checkpoint

Branch: `release/2026-10-28-integration` in `.release-local`. Report date: 27 October 2026. Read `FINAL_RELEASE_REPORT.md` for exact scope and evidence.

## Completed

- Events schema failure repaired; current migration e0f1a2b3c4d5.
- India directory/filter/discovery integration, CSV/XLSX review imports, publication, duplicate review/merge/provenance and safe aliases.
- Account personalization, deterministic recommendations, notifications/preferences and idempotent in-app reminder worker.
- Docker migration dependency and schema readiness; reviewed prediction data included in image.
- Full backend 483 pass/11 deliberate PG skips; all11 PG cases separately passed. Frontend20 pass/1 opt-in skip; opt-in test separately1 pass. Collector157, module33, operations66 pass. Browser30+4+6 checks passed. Lint/build/infra checks passed.
- Actual local counts5 events/3users/3saved/1362institutions across33states/UTs. Restart identities and fresh backup restoration verified.
- Final narrow annual-URL guard validated by affected ingestion regression tests; final backend image rebuilt and applied.

## Exact next acceptance action

Obtain current permission evidence and a human review decision for one real supplied event dataset. Do not turn an old AI-review attestation into human approval. In React Admin ? Sources, register the permission-backed source; upload its CSV/XLSX with the exact reference; review/publish the accepted candidate; confirm its event appears in Explore. Keep live collection disabled unless separately authorized and robots compliant.

Then obtain verified historical outcome labels for temporal evaluation, and authorized SMTP test credentials/recipients if email is required. Public deployment remains unexecuted pending infrastructure configuration/authorization.

## Reproduction

```powershell
Set-Location C:/Users/nakul/OneDrive/Documents/Desktop/hackathonradarfinder/.release-local
docker compose -p hackathonradarfinder up -d --build
# Performs local restart and checks preserved identities + proxy endpoints:
backend/.venv/Scripts/python.exe scripts/verify_local_release.py
# Isolated PostgreSQL + built-image/browser acceptance:
backend/.venv/Scripts/python.exe scripts/postgres_acceptance.py --backend-image hackathonradarfinder-backend:local --frontend-image hackathonradarfinder-frontend --out .test-support/recheck
```

Keep `.local-backups` and `backend/.env` private. Do not reset volumes. Separate restore-verification databases remain for inspection. Raw reports and screenshots are in `.test-support`; concise committed evidence is in `docs/release-evidence/2026-10-27`.

Accidental terminal-output files and separate untracked scraper work are preserved and excluded from commits. No protected branch was modified; no remote push/PR/public deployment is claimed.

# Release checkpoint

27 October 2026; `.release-local`; `release/2026-10-28-integration`.

## Verified state

- Merge-conflict reconciliation: `8d9ac82d3751857fdc46e66a884ee4229d2a16e2`, pushed. PR #96 is already merged externally, merge SHA `4592c030782c75ba73bcde0c040f27c63d697533`. Do not reopen/remerge it or repeat its audit.
- Completion commits: `146bda7`, `2fd2dc9`, subsequent URL repair and evidence handoff. Check `git log -5` and the follow-up draft PR for final HEAD/CI status.
- PostgreSQL migration `e0f1a2b3c4d5`; unchanged IDs/selected values for 5 events, 3 users, 3 saved items and 1362 universities (1362 identifiers, 33 states/UTs). No reimport/reset is needed.
- Profile editing, directory pagination/search/state filtering, batched imports and normalized review URLs are implemented. Complete publication/duplicate workflow passed against owned synthetic fixtures.
- Final evidence is in `docs/release-evidence/2026-10-27-final/`; local raw outputs are ignored under `.test-support/final-handoff/`.
- Unrelated `hackathon_radar_scraper/` remains untracked and preserved. Do not stage it or generated caches/dumps.

## Next real-data action

A human must inspect the exact Brabble pilot facts and add an explicit dated, fact-bound approval preserving acquisition evidence and provider credit. The supplied row is AI-reviewed, not human-approved. Validate first without `--apply`; use `--check-target` before authorized application to the exact database. Do not project away provider evidence through generic CSV to bypass this gate. API-row reuse permission does not authorize direct upstream scraping.

Other external inputs are verified historical outcomes for temporal validation/calibration, authorized SMTP/test recipients, and an owner deployment decision/infrastructure. Keep integrations disabled until their requirements are met. See `REMAINING_BLOCKERS.md`.

## Reproduce only affected checks

From `.release-local`:

```powershell
backend/.venv/Scripts/python.exe scripts/read_only_release_smoke.py
# Only when another restart/persistence check is necessary:
backend/.venv/Scripts/python.exe scripts/verify_local_release.py
# Owned disposable PostgreSQL and built-image acceptance:
backend/.venv/Scripts/python.exe scripts/postgres_acceptance.py --backend-image hackathonradarfinder-backend:local --frontend-image hackathonradarfinder-frontend --out .test-support/new-acceptance
```

For full backend checks, run `.venv/Scripts/python.exe -m pytest tests -q` from `backend`. The normal suite intentionally skips gated PostgreSQL cases; the owned runner executes all 13. See `DEMO_CHECKLIST.md` for fixture-only admin credentials, synthetic CSV, startup, safe shutdown and limitations.

Do not repeat the completed audit/build/import. Never reset persistent volumes, invent approvals/metrics/delivery, merge a protected branch or deploy publicly without the owner's explicit instruction. The final remote workflow result belongs to the exact pushed HEAD and must be checked separately from local tests.

# Current launch/demo notes

The local app is at http://127.0.0.1:5173; the collector service is included in the workers profile. SMTP/email controls are disabled; demonstrate in-app notification read state instead. Do not request SMTP credentials for launch.

Release review is PR #100, not PR #98/#99. Check the repaired head's CI before owner review. Production Compose and restart/backup/restore were verified in an owned disposable stack; public hosting/DNS/secrets remain external requirements. Preserve the existing database and its 1362 institutions.

Organizer collection must use COLLECTOR_RAW_DATA_DIR=/app/collector-data/raw on the persistent collector volume. Brabble API snapshots use COLLECTOR_SNAPSHOT_DIR. Never enable a source without its actual permission evidence/key, and never publish pending rows automatically.

---

# Hackathon Radar Finder demo checklist

## Start the existing local application

From `.release-local`:

```powershell
docker compose -p hackathonradarfinder up -d --no-build
docker compose -p hackathonradarfinder ps
```

Use `--build` only after source changes. Preserve `backend/.env`, the PostgreSQL volume and the imported universities. A migration service runs before backend startup. No production deployment is implied.

- Application: http://127.0.0.1:5173
- API docs: http://127.0.0.1:8000/docs
- Readiness: http://127.0.0.1:5173/api/ready
- University directory: http://127.0.0.1:5173/universities

## Accounts and isolated administrative demonstration

For the persistent local app, register an ordinary account or use existing project-owner-approved credentials. Public registration cannot create an administrator. Do not reset another account or grant roles to improvise a demo.

For source upload/review/duplicate demonstrations, use the existing disposable fixture instead. It creates temporary SQLite data and never uses the configured PostgreSQL database.

Terminal A, from `.release-local/backend`:

```powershell
.venv/Scripts/python.exe ../scripts/disposable_backend.py --port 8020
```

Terminal B, from `.release-local/frontend`:

```powershell
$env:API_PROXY_TARGET='http://127.0.0.1:8020'
npm run dev -- --port 5180 --strictPort
```

Open http://127.0.0.1:5180 and confirm http://127.0.0.1:5180/api/__disposable_fixture returns `temporary-sqlite-frontend-tests`. Only that marked fixture has the public synthetic test account `admin@example.com` / `DisposablePassword123!`. These are fixture credentials, never persistent-service credentials. Stop both terminals when finished.

## Main demonstrations

1. Persistent application, read-only directory: Universities -> inspect total -> next page -> state `Uttar Pradesh` -> full university name -> empty search -> reset. Directory coverage does not imply event coverage or collection permission.
2. Ordinary user: register/login -> keyword/mode/date filters -> details -> official registration/organizer link -> save -> Preferences -> change display name and interests -> read notification -> logout/login -> confirm saved state. Reloading the page ends the in-memory login session by design.
3. Disposable administrator: Admin -> Sources -> Register source. Use a clearly synthetic source key, `events-json-v1`, URL `https://example.org/synthetic-demo`, reference `synthetic-demo-only`, basis `Synthetic records owned by this disposable demonstration`, and real current timezone-aware reviewed/expiry timestamps. Enable this source only in the marked fixture. No collection worker is started.
4. Upload `docs/demo/synthetic-events.csv` **only to that disposable fixture**, with the matching reference. The file is explicitly fictional; never upload it to the persistent catalog. Import stages three pending candidates; repeating it creates none.
5. Review -> inspect each synthetic candidate -> supply an explicit demonstration rationale -> approve/publish. Confirm catalog details and discovery history. Show rejection on another synthetic candidate if desired; already reviewed records cannot be approved twice.
6. Duplicates -> inspect the two synthetic Buildathon records -> review merge -> enter rationale -> confirm. Verify one retained record, preserved provenance and audit history. Reimporting the file must not resurrect the duplicate.
7. Preferences -> show profile/interests and in-app read/unread notices. Email-only controls are hidden and SMTP is disabled.
8. Predictions -> show readiness and withheld forecasts. Five reviewed historical editions are insufficient for calibrated public predictions. Synthetic forecasts are test fixtures only.

## Safe restart and checks

```powershell
backend/.venv/Scripts/python.exe scripts/read_only_release_smoke.py
# The next command restarts the local application and compares stored identities/values:
backend/.venv/Scripts/python.exe scripts/verify_local_release.py
```

The restart verifier checks events, saved items, users and institutions without printing their personal contents. It does not delete volumes or reimport records. Keep backups and `.env` private.

## Troubleshooting and limitations

- API unavailable: inspect `docker compose -p hackathonradarfinder ps`, `/api/ready` and backend logs. A readiness migration failure needs the existing backup/reviewed migration procedure; do not reset the database.
- Anonymous after refresh: sign in again; credentials/tokens are not stored in browser storage.
- Admin 403: use an authorized administrator account or the disposable fixture. Never bypass the backend role check.
- Source rejected: check current permission evidence, exact reference, enabled state and timezone-aware approval dates. Do not fabricate approvals.
- Empty events/recommendations: use actual catalog dates; some records are historical. Broader real publication needs human approval. Empty readiness/results are deliberate, not fabricated data.
- Email not delivered: live delivery remains disabled; no SMTP/inbox success is claimed.
- Fixture missing: check ports 8020/5180 and `API_PROXY_TARGET`. Never remove a real database volume to repair a fixture.

See `FINAL_RELEASE_REPORT.md` for actual results and `REMAINING_BLOCKERS.md` for genuine external dependencies.

## Factual-review sprint

The current non-importable worksheet, two-candidate factual shortlist and 23-candidate blocked list are in `backend/radar_collector/output/factual-review-20261028/packet/`. Use them for human review only; no human signoff exists. See `docs/reviews/FACTUAL_REVIEW_20261028.md`. Do not upload this worksheet or publish pending records.

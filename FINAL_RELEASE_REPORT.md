# Release stabilization handoff

PR #100 is the existing main-history bridge; no duplicate PR or protected merge was created. At 034b4716c523a195825d5af6312f6a486160dd5c, [CI](https://github.com/HackathonRadarFinder/hackathonrdarfinder/actions/runs/40734796936) and [Module 2.4](https://github.com/HackathonRadarFinder/hackathonrdarfinder/actions/runs/40734796812) passed. The bridge has zero file differences from develop and keeps the old main tip d968e3978284b557a255fee5a9051b206ec3a5ea as an ancestor. Original main remains recoverable without a reset or history rewrite.

One focused repair corrects RAW_DATA_DIR to COLLECTOR_RAW_DATA_DIR in local/production Compose. The previous value was ignored by the actual organizer collector loader and could leave raw snapshots outside the durable volume. Both direct configuration checks passed and a regression was added; repair CI, not the older green run, determines readiness of the new head. No collector redesign, full audit, dataset reimport or image rebuild was performed during stabilization.

| Area | Result | Evidence | Blocker |
|---|---|---|---|
| PR #100 | Existing draft; history bridge verified | Previous exact-head CI green; zero develop file differences before repair | Repair CI, owner review/merge |
| Backend | Ready locally | HTTP readiness: connected/current; prior focused regressions reused | None beyond repair gate |
| Frontend | Integrated | Prior 30 browser checks, 22 axe scans; 7 admin and 5 college checks | None |
| PostgreSQL | Preserved | 5 events/3 users/3 saves/1362 institutions; stored-value hashes unchanged | None |
| Scheduler | Implemented and restart-tested | Owned production Compose run: schedule, lock, recovery and backup/restore passed | Raw-storage configuration repair CI |
| Live acquisition | Not tested with real credentials | Missing Brabble key; provider mocks passed 14 tests | Authorized key and source policy |
| Review/publication | Human gate retained | 25 candidate review packet; two factual drafts; zero new real publications | Real human approval and conflicting facts |
| Colleges | Directory ready; no invented matches | 1362 entries; 0 verified event associations, 0 upcoming associations | Verified publication links |
| ML | Honest insufficient-history status | 5 editions/1 recurring series/0 folds; public forecasts disabled | Sufficient earlier observations/outcomes |
| Production Docker | Isolated stack verified | Non-root images, scheduler recovery, persistence and backup/restore passed | Hosting/DNS/private production configuration |
| Public deployment | No | Local application only at http://127.0.0.1:5173 | Owner authorization and real infrastructure |

SMTP is disabled in release Compose and email-only controls are hidden. In-app notifications remain available. SMTP credentials/delivery are no longer launch requirements. Older report sections below are historical, including superseded email blockers.

No secrets, generated collector datasets or dumps are tracked by the scoped path check. The untracked scraper and accidental terminal-output file were preserved. Local tests requiring elevation were unavailable because automatic approval review hit a usage limit; that rejected command was not executed. No bypass or fabricated passing test result is claimed. The added regression is intended for the new commit's CI.

Exact next action: inspect PR #100's checks for the repair commit once; if green, the owner reviews and decides whether to merge. Configure real private deployment secrets/domain/hosting and authorized API/source policy separately. Do not equate a main merge with public deployment.

---

# Final execution sprint: 28 October 2026

Fresh branch: `fix/2026-10-28-factual-review`, based on `origin/develop` after PR #97 was confirmed merged externally (`c996f16e9d5f737d8b3a7fcd99fb11e38ac6c9ae`). No duplicate PR #96/#97 was created, protected branch merged or production deployment performed by this sprint. The earlier release report below remains historical evidence.

| Component | Status | Current evidence | Remaining blocker |
|---|---|---|---|
| Backend | Targeted regressions pass | 174 passed, 0 failed/skipped; importer/approval/notifications/ML | None for scoped code changes |
| Frontend | Existing integration passes | 23 passed, 1 opt-in backend smoke skipped; lint passed; real reviewed pilot reaches React cards | Full browser/build not repeated locally; CI checks current commit |
| PostgreSQL | Preserved | Read-only IDs/selected-value hashes match previous snapshot; 5 events, 3 users, 3 saved items, 1362 institutions; migration e0f1a2b3c4d5 | No data reimport needed |
| Data collection | Existing acquisition retained | Six immutable pilot/review input hashes unchanged; original provenance and Brabble credit retained | New API acquisition requires an authorized key; no live source scraping enabled |
| Factual review | Complete 25-candidate worksheet | 225 fields: 48 primary-supported, 9 conflicts, 10 indexed leads, 3 unknown, 155 unverified | 23 candidates still need factual resolution; human decisions listed in review report |
| Data publication | Correctly gated | Two factual drafts await human consideration; zero human approvals/new persistent staging/publication | Real dated fact-bound human approval; worksheet is deliberately non-importable |
| ML predictions | Suppressed | Current baseline evaluation: 5 editions/1 recurring series/0 folds; separate 3-edition retrospective research also 0 folds | Sufficient genuinely earlier observations and outcome labels; no invented availability times |
| Notifications | Mock/dry-run ready | Consent, retries, deduplication, failure/read-state regressions included in 174 | Authorized SMTP configuration and recipients; no real email sent |
| Docker | Existing app healthy | Backend, PostgreSQL, frontend healthy; ready/current migrations | Current source affects offline review workers; local runtime was not rebuilt/restarted unnecessarily |
| Release readiness | Locally demo-ready; scoped review candidate | Focused fixes/tests, reports and selective commits; final remote status is linked in the new PR | Human review and owner production decision; not production-ready |

## Work completed

- Added a reproducible, database-free field-review packet builder. It validates original provider evidence, requires one observation per candidate, separates verified proposals from conflicting/unverified claims, preserves attribution, hashes inputs and emits the five requested review deliverables. Generated CSV/JSON datasets remain ignored locally.
- Fixed acceptance of future-dated factual reviews/human approvals, approvals predating factual review, and a direct-human approval path that previously returned before revalidating facts. Added six chronology regressions.
- Extended disposable real-pilot acceptance to check search, mode, location, organization filters and empty search using the React catalog query contract. No pending records were applied.
- Reviewed all 25 candidates. BID AND CODE and Hacknauts are the two factual drafts awaiting human consideration. No new bound review ledger/approved CSV or invented human identity was created. The existing one AI-reviewed row remains the only importable pilot row for disposable acceptance.
- Built an isolated historical research dataset for Megathon 2022, 2023 and 2025 from institutional retrospectives. Observation timestamps are today, not historical publication dates. Baseline evaluation correctly yields zero valid folds. Production trust manifests/models and public prediction settings are unchanged.

Read [the factual findings and human decisions](docs/reviews/FACTUAL_REVIEW_20261028.md). The full 225-field report, corrected CSV, shortlist, blocked list and retained acquisition evidence are local at `backend/radar_collector/output/factual-review-20261028/packet/`. Generated datasets, caches, dumps, credentials and the unrelated `hackathon_radar_scraper/` are excluded from commits.

## Actual validation and initial failures

- Final affected suite: **174 passed, 0 failed, 0 skipped** (one upstream Starlette/httpx deprecation warning). Includes import, pilot/worksheet, approval, notifications and temporal evaluation. Counts overlap earlier tests and must not be summed.
- Frontend: **23 passed, 1 skipped, 0 failed**; the skipped opt-in fixture test requires its separately running server. The default suite did execute the existing genuine reviewed-pilot import/API/React-card test. Lint passed.
- Initial sandbox runs failed to create/read pytest temporary directories and spawn Node workers. Rerunning the isolated tests with appropriate execution permissions resolved those environmental failures.
- The new packet tests initially failed because their fixture CSV was not checked in. The test now generates it from existing immutable fixtures with `prepare_pilot`; all eight packet cases passed afterward.
- An initial standalone pilot command inherited invalid `DEBUG=release`. Re-execution with explicit isolated settings passed; no environment file was edited. The final regression suite executes the updated pilot search/filter acceptance.
- ML baseline CLI ran: all MAE/calibration/coverage metrics null, no valid folds. No accuracy/delivery claim.
- Python compile, whitespace and conflict-marker checks passed. Current run evidence summaries are in `docs/release-evidence/2026-10-28-sprint/`. Full unaffected backend/browser suites and local image builds were not repeated.

## Commands and safe continuation

From `backend`, with test-only configuration for standalone acceptance:

```powershell
$env:DEBUG='false'
$env:DATABASE_URL='sqlite+pysqlite://'
$env:SECRET_KEY='isolated-sprint-test-secret-key-20261028'
.venv/Scripts/python.exe -m workers.build_factual_review_packet --candidates radar_collector/output/brabble-pilot/pilot_candidates.csv --observations radar_collector/output/factual-review-20261028/research_observations.json --out radar_collector/output/factual-review-20261028/packet
.venv/Scripts/python.exe -m workers.accept_brabble_pilot --csv radar_collector/output/brabble-pilot/reviewed.csv --out ../.test-support/new-pilot-acceptance
.venv/Scripts/python.exe -m pytest tests/test_factual_review_packet.py tests/test_brabble_pilot.py tests/test_reviewed_public_import.py tests/test_brabble_ingestion.py tests/test_brabble_refresh.py tests/test_email_notifications.py tests/test_notifications.py tests/test_temporal_prediction.py tests/test_prediction_policy.py -q --basetemp ../.test-support/new-sprint-tests
.venv/Scripts/python.exe -m workers.evaluate_predictions --output ../.test-support/new-ml-evaluation.json
```

Other commands executed: `git fetch origin develop`; create fresh feature branch; `npm test`; `npm run lint`; GET-only release smoke; read-only database snapshot; `docker compose ... ps`; compile and selective Git checks. Do not reuse temporary output paths that the evaluator refuses to overwrite. No `--apply` is authorized by a shortlist. Preserve `.env`, existing databases, untracked datasets and scraper directory.

Final commit/PR links and exact remote check outcomes are reported after push in the new PR/final handoff; earlier CI is not substituted for current-source verification.

---

# Final release report

Updated 27 October 2026. Worktree `.release-local`, branch `release/2026-10-28-integration`.

## Release status

The local application is verified and demo-ready within the limits below. Real publication beyond the existing catalog, validated public forecasts, live email and production deployment still require external evidence or owner decisions. No claim of 100% completion is made.

Module 2.4 conflict reconciliation was committed and pushed as `8d9ac82d3751857fdc46e66a884ee4229d2a16e2`. It preserves the release API, master database/schema mappings and advanced deduplication while retaining compatible PR #95 fixes/tests. PR #96 was subsequently merged externally into develop as `4592c030782c75ba73bcde0c040f27c63d697533`; this session did not merge a protected branch. The new completion work requires a separate draft review PR.

## Completed behavior

- Authentication, revocation, database-authoritative administrator roles, account display-name editing with strict field limits and no email/role escalation. Stale responses cannot restore a logged-out session.
- Catalog search/filter/sort/pagination, details, saved events, private preferences, explainable deterministic recommendations and notification read state.
- Public Universities page with search, state filtering, pagination, empty/error/loading states and responsive accessibility checks, using the existing 1362-row directory.
- Source permission registration, CSV/XLSX validation, staged candidates, explicit review/publication, provenance, audit trails and conservative duplicate merging with saved-reference preservation and reimport aliases.
- Imports batch existing-identity queries and flush once. A 1000-row import now uses 3 SELECTs rather than the measured previous 1001. In-batch duplicates share a candidate.
- Homepage URLs normalize consistently before staging and review. Encoded private addresses are checked again after normalization; root URLs no longer fail the immutable review identity check.
- Reviewed history, temporal evaluation/readiness, optional reminder workers and guarded email queue/dry-run paths. Unvalidated forecasts and live external integrations stay disabled.

## Persistent database preservation

PostgreSQL 16 remains at Alembic head `e0f1a2b3c4d5`. Upgrade/restart checks compared IDs and selected stored-value hashes before and after: **5 events, 3 users, 3 saved items, 1362 institutions**, all unchanged; **1362 unique institution identifiers across 33 states/UTs**. Hashes omit passwords/secrets and reports contain no personal row contents. No university reimport or volume reset occurred. Existing private backups remain ignored; previous restore verification is recorded in earlier evidence.

All new write-based acceptance used ownership-verified disposable databases. The directory browser smoke used GET/HEAD/OPTIONS only and blocked writes. The persistent local app is available at http://127.0.0.1:5173, with readiness at `/api/ready`.

## Actual ingestion status

The existing Brabble export contains 206 rows (195 Unstop, 11 Devfolio). The selected 25-row pilot and reviewed one-row CSV refer to the same single AI-reviewed Hacknauts 2.0 event; **zero records have the required value-bound human approval**. The apply gate correctly blocks publication. This execution did not invent approval or publish those records into the persistent catalog.

The [Brabble API reference](https://brabble.ai/docs) permits reuse of API rows with provider attribution; its terms were inspected during this release work. This does not authorize direct upstream scraping or replace factual human review. Preserve acquisition evidence and credit. After real review, validate with the reviewed-public importer before explicitly applying to the checked target. See the pending, deliberately incomplete template in `docs/release-evidence/2026-10-27-resume/`.

The complete source registration -> upload -> review -> publication -> duplicate merge -> reimport workflow passed using explicitly synthetic disposable fixtures. The included `docs/demo/synthetic-events.csv` is solely for the marked disposable demo. University directory coverage is not event coverage or collection permission.

## Tests and measurements

Final machine-readable evidence: `docs/release-evidence/2026-10-27-final/`. Suite counts overlap and must not be summed as unique coverage.

| Validation | Actual result |
|---|---|
| Full backend | 491 passed, 13 gated PostgreSQL tests skipped (executed separately below) |
| Owned PostgreSQL 16 / built images | 13 passed, zero failures/skips; browser passed |
| Frontend default tests | 23 passed, 1 skipped |
| Opt-in frontend/backend test | 1 passed, zero skips |
| Module 2.4 | 35 tests passed |
| Offline governed collector | 157 passed |
| Operations safeguards | 67 passed |
| Frontend lint and production image build | Passed |
| Python compile and conflict checks | Passed; no Module 2.4 conflict markers |
| Base browser | 30 checks; 22 axe scans without violations |
| India workflow browser | 4 checks |
| Upload/review/profile/personalization browser | 7 checks; zero browser errors |
| Universities read-only browser | 4 checks; zero browser errors; responsive/a11y checks |

Browser sizes included 320, 390, 768 and 1440 px. Final images ran as backend `10001:10001` and frontend `101:101`; the owned acceptance containers were removed without deleting persistent volumes.

On owned disposable PostgreSQL, 1000 synthetic candidates staged in **0.309 s**, repeated in **0.192 s**, with 3 SELECTs each and zero published events. This is a local capacity observation, not a load benchmark. GET-only loopback samples (five successes per route) recorded medians of 20.77 ms for events, 15.90 ms for institutions and 18.18 ms for institution search. Invalid pagination returned 422; anonymous admin access returned 401. Raw reports preserve exact values/environment limits.

## ML and notifications

Actual temporal evaluation has **5 reviewed editions, 1 recurring series and 0 valid held-out folds**. MAE, coverage and calibration stay null; readiness is insufficient history and public forecasts are disabled. Illustrative Module 2.4 labeled pairs are not an independent accuracy benchmark. Real historical occurrence labels and observation timestamps are needed.

Notification consent, reminder idempotency, read state, retries, precision changes and ambiguous transport outcomes have isolated test coverage. Transport used mocks/dry-run only; no SMTP acceptance or inbox delivery is claimed. Live email remains disabled until explicitly authorized configuration and recipients exist.

## Git and handoff

Implementation commits include `146bda7` (private profiles/batched imports), `2fd2dc9` (profile UI/university directory), plus `0340d25` (final URL-normalization repair) and this evidence handoff. Use `git log -5 --oneline` for exact final commits. Changes are committed selectively; unrelated `hackathon_radar_scraper/` remains untouched/untracked. Caches, output, dumps, credentials and accidental files are excluded.

Prior remote CI and Module 2.4 workflows passed for `8d9ac82`. Final-HEAD remote checks are verified after push and reported with the follow-up PR/final handoff; that result is not inferred from earlier CI or local tests. No force-push, rebase, public deployment or new protected-branch merge is authorized.

See [DEMO_CHECKLIST.md](DEMO_CHECKLIST.md) for reproducible startup and demonstration, [RELEASE_CHECKPOINT.md](RELEASE_CHECKPOINT.md) for continuation, and [REMAINING_BLOCKERS.md](REMAINING_BLOCKERS.md) for the four external dependencies.

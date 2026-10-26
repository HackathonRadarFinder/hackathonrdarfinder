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

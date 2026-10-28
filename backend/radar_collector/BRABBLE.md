# Brabble API ingestion and controlled refresh

## Current snapshot

The supplied brabble-live exports contain 195 Unstop and 11 Devfolio listings.
They came through Brabble.ai, not direct scraping. The normalizer joins each
export to its original API record by provider ID and checks source URL/platform.
It handles UTF-8 BOMs and reversibly repairs mojibake in display labels while
retaining original raw values. See output/brabble-review/quality_report.json and
quality_report.md for file checksums, missing fields, schema failures and counts.

The original HTTP response envelopes were not supplied. Acquisition and refresh
timestamps are preserved from hackathons.json, not reconstructed from file mtimes.
A checksum labelled api_record_sha256 covers canonical JSON of each supplied API
record. It is not an HTML hash, proof of transport, or proof that an organizer has
independently verified a listing. New refresh runs also retain response envelopes.

All 206 initial records remain needs_review. The 11 Devfolio organizer strings
'See listing' become unknown. Missing venue/prize placeholders become blank. Modes
map to Online/Offline/Hybrid. The city field is retained as a location description,
not elevated into a verified venue. No numeric prize is invented from a label.
Raw prize.inr, team, fee, eligibility and registered counts remain in evidence;
prize labels/counts are provider supplied and may be incomplete or incomparable.

The API kind governs deadline meaning: competition means registration/application
close; contest means contest start. All 206 supplied kinds are competition.
No event start or end date is inferred from those deadlines. An unknown event date
may be explicitly reviewed as unknown; never fill it with the registration deadline.

## Review and import

Use the existing reviewed CSV importer. There is no Brabble write endpoint, new
DB schema, automatic publication or replacement discovery service. API evidence
is stored in EventVersion.changes.acquisition. Public /events/ list/detail and
/account/saved responses expose a bounded attribution view; raw records and internal
review flags stay in history. React cards (including saved cards) and details
show visible linked Brabble.ai attribution, original platform and refresh times.

From .release-local/backend, generate a NEW review output directory per refresh:

```powershell
$env:DEBUG = 'false'
.\.venv\Scripts\python.exe -m workers.prepare_brabble --input radar_collector/output/brabble-live --out radar_collector/output/brabble-review
.\.venv\Scripts\python.exe -m workers.import_reviewed_public radar_collector/output/brabble-review/candidates.csv
```

The initial dry-run reports approved_and_valid=0, not_approved=206, applied=false.
Copy candidates.csv to a reviewer-owned file before edits; regeneration overwrites
that output. review_queue.json contains the same normalized candidates with
structured acquisition_evidence; candidates.csv stores that object as JSON in one
cell. candidates.json is the CSV-shaped inspection copy. The existing importer
accepts CSV only, preventing a second write path.

For each real record to approve:
1. Verify organizer, original-platform URL and deadline meaning against authorized
   evidence. Record missing start/end as unknown. Do not use restricted scraping
   to resolve missing fields. If evidence is insufficient, keep needs_review.
2. Correct factual fields in the reviewer copy. Keep original raw_record unchanged
   and retain any additional verification evidence with the reviewer’s records.
3. In that row's acquisition_evidence JSON, set verified_fields to
   ["organization","url","dates"] only after those checks. Keep method=brabble_api,
   provider ID, original URL/platform, provider share URL, original acquisition and
   refresh timestamps, and api_record_sha256 unchanged. Leave source_hash blank.
4. Retain permission_reference to the reviewed API reuse terms and set
   review_status=approved only for verified rows. Source remains Unstop/Devfolio;
   Brabble.ai is the acquisition provider, not the event organizer.
5. Dry-run the edited CSV; an invalid approved row rejects the batch before writes.

After review and explicit selection of a DEVELOPMENT target DATABASE_URL:

```powershell
# Inspect target configuration and apply existing Alembic migrations first.
.\.venv\Scripts\python.exe -m workers.import_reviewed_public C:\PATH\reviewed-brabble.csv
# This next command writes ONLY approved rows; do not run it on the initial queue.
.\.venv\Scripts\python.exe -m workers.import_reviewed_public C:\PATH\reviewed-brabble.csv --apply --reviewed-by REVIEWER_ID --expect-database hackathon_radar
```

The CLI is dry-run by default. Applying uses the existing transaction/savepoint,
SQLite writer serialization or PostgreSQL event-table lock, organization lookup
and EventVersion provenance. Normalized existing URLs are skipped across sources;
Brabble provider IDs also prevent new events when a provider changes a slug.
Duplicates never overwrite curated records. A failed batch rolls back its event,
organization and version writes; caller rollback undoes successful staging too.
PostgreSQL locking is implemented but needs PostgreSQL validation before deployment.
Unrelated writers still lack a database-wide canonical URL uniqueness constraint;
review aliases/redirects before importing. Matching IDs are skipped, not refreshed
in place: changed facts need an explicit separate review/update, never blind upserts.

## Authorized API-only refresh schedule

Reference: https://brabble.ai/docs and https://brabble.ai/developers
The API uses GET https://brabble.ai/api/listings with a backend-only bearer key.
Current documented allowance is 1000 requests/day, reset at midnight IST.
Responses report remaining quota; snapshots expose refreshedAt separately from
acquisition time. Preserve visible credit and a Brabble link. Hourly polling is
ample; never fetch once per frontend request or ship the key in VITE_* variables.

The new refresh worker defaults to a no-network plan:

```powershell
.\.venv\Scripts\python.exe -m workers.refresh_brabble
```

After API access is authorized, provision BRABBLE_API_KEY through the scheduler's
secret environment (Credential Manager/secret manager or a restricted backend
service environment). Do not put the key in source, task arguments, URLs, frontend
configuration, report files or logs. Then the operator can explicitly collect:

```powershell
.\.venv\Scripts\python.exe -m workers.refresh_brabble --collect
```

This command was NOT executed with live collection during development. It only
calls the Brabble API; redirects are refused and the key is never forwarded to
Unstop/Devfolio. It creates a new timestamped snapshot directory, stores original
API envelopes and per-page acquisition timestamps, and never writes the DB.
A failed/incomplete API collection does not publish a snapshot. Retain snapshots
as immutable evidence; do not point --out at an existing directory.

Configure a disabled-by-default Windows Task Scheduler task with backend as the
working directory and the existing virtualenv Python as executable. After access
and secret provisioning, schedule at most hourly, disallow overlapping instances,
and pass -m workers.refresh_brabble --collect. Configure alerts on nonzero exit.
Each run has a hard 20-request cap INCLUDING retries, requests are separated by at
least one second, transient network/5xx errors have at most three attempts, and
pagination stops on low remaining quota. One hourly task consumes at most 480
requests/day; shared API-key usage must also fit the provider allowance. On 429,
stop scheduling until the documented midnight-IST reset; no bypass/retry storm.
401/403/redirects stop immediately. Review actual remaining-quota headers and
adjust cadence downward when sharing a key. API contracts can change; recheck docs
before enabling a schedule. Do not register Brabble as unstop-v1: that adapter is
for a different governed direct-collection path. No discovery source is enabled.

After each successful snapshot, run prepare_brabble on its directory into a new
review directory, then review and dry-run. Scheduled acquisition never sets
review_status=approved and must never chain --apply automatically. The separately
restricted Unstop/Devfolio approvals.json flags remain false and unchanged.

## Tests

```powershell
# From .release-local/backend:
.\.venv\Scripts\python.exe -m pytest tests/test_brabble_ingestion.py tests/test_brabble_refresh.py tests/test_reviewed_public_import.py tests/test_scraper_ingestion.py tests/test_discovery.py tests/test_discovery_history.py tests/test_event_pagination.py tests/test_events_services.py tests/test_account_integration.py radar_collector/tests -q
# From .release-local/frontend:
npm test
npm run build
npm run lint
```

All database writes in tests go to temporary SQLite. The frontend integration
spawns scripts/brabble_ui_fixture.py, which commits two clearly synthetic reviewed
API records to disposable SQLite, retrieves them through FastAPI /events/, then
renders actual React EventCard components through the existing API client.
It never approves the real review queue or touches development/production data.
The optional pre-existing frontend external-backend smoke test stays skipped
unless its separate disposable-server environment variable is set.


## First real-data pilot (25 October 2026)

See PILOT_ACCEPTANCE.md for the 25-record evidence checklist, one explicitly
reviewed real record, disposable end-to-end results and current Docker blocker.
The original 206-row queue remains unapproved and unchanged.

Brabble approvals now require acquisition_evidence.review in addition to the
legacy verified_fields flags. Metadata must identify reviewer and type, timestamp,
API permission basis, per-field checks (verified for present values, unknown for
blank values), date precision, and a hash binding the reviewed EventCreate values.
A change to reviewed facts or precision requires another review. Unresolved
conflicts prevent approval. This is a reviewer attestation, not proof of a human
review: the pilot explicitly identifies its reviewer as an AI assistant acting
on the user's request. Synthetic test attestations cannot be applied via the CLI.
--apply now also requires an exact --expect-database and refuses non-development,
remote, production-named or ambiguous targets. --check-target only inspects
redacted configuration; it does not claim a connected server was verified.

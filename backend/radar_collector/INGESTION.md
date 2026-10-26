# Reviewed public-event ingestion

Run from `.release-local/backend` with `.venv/Scripts/python.exe`.
This workflow uses existing Hackathon, Organization and EventVersion tables.

## Review contract and real-record workflow

1. Retain authorization and terms review for each platform and acquisition
   method. Live HTTP additionally requires documented approval in approvals.json,
   a valid RADAR_CONTACT_EMAIL, robots permission and compliance with rate limits.
   Both sources are currently disabled. Access challenges, CAPTCHA, login walls,
   robots denial and HTTP 401/403/429 are stop conditions, never bypass targets.
2. Retain authorized source HTML and its SHA-256. Verify factual fields against
   evidence, preserving blank optional data. Missing organizer prevents approval.
3. Each approved CSV row needs review_status=approved, title, organizer,
   description, source URL, source attribution, collection timestamp,
   source_hash (64 hex digits), date_precision (unknown/day/exact),
   collection_mode (live_public/reviewed_manual), and permission_reference
   identifying retained permission evidence for that source/acquisition method.
   live_public is emitted by the governed public-page collector; reviewed_manual
   is for independently authorized manual acquisition. Never relabel fixtures.
   These fields are reviewer attestations, not cryptographic authorization.
4. Dry-run the reviewed real CSV, inspect results, then explicitly apply it to
   the intended migrated database with an identified reviewer:

```powershell
$env:DEBUG = 'false'
.\.venv\Scripts\python.exe -m workers.import_reviewed_public PATH_TO_REAL_REVIEWED.csv
# Only after reviewing real records and confirming the target DATABASE_URL:
.\.venv\Scripts\python.exe -m workers.import_reviewed_public PATH_TO_REAL_REVIEWED.csv --apply --reviewed-by REVIEWER_ID --expect-database hackathon_radar
```

5. Verify GET /events/ and GET /events/{id}. Source and URL are public fields;
   HTML hash, reviewer, review timestamp, permission reference, acquisition mode
   and date precision are retained in EventVersion.changes.

The importer validates the entire approved batch before writes, never overwrites
existing event URLs, and commits only an entirely successful CLI import.
A savepoint rolls back event, organization and provenance writes together.
Successful staging can still be rolled back by its caller. SQLite serializes
writers before duplicate reads; PostgreSQL takes a transaction-scoped event-table
write lock. PostgreSQL behavior still needs validation against PostgreSQL; tests
use disposable SQLite. Other dialects fail closed. This is not a database-wide
uniqueness constraint on unrelated writers. Incoming tracking parameters and
trailing slashes are canonicalized. Legacy aliases, changed slugs and redirected
URLs still need manual reconciliation; matching canonical URLs skip duplicates
across sources without overwriting existing records.

## Offline schema audit

Exports are candidate envelopes, not direct EventCreate payloads. The CSV importer
selects EventCreate fields and converts blank optional values to null. JSON is an
inspection format, not a second ingestion path. Three supplied candidates validate
after that conversion; DevNexus lacks an organizer and must remain pending.
All four are needs_review/offline_fixture and none may be imported as real events.
The importer rejects approved fixture rows and legacy approved rows without
acquisition metadata. Retain original source evidence separately from editable CSV.
Day-precision midnight is a storage convention, not an announced event time.

## Future authorized Devfolio scheduler support

SourcePolicy currently supports only curated-v1 and unstop-v1. The latter handles
Unstop API JSON through normalize_unstop_collection, not candidate HTML. Unknown
adapters now fail closed both in policy evaluation and collection dispatch.

Future Devfolio work must add an explicitly reviewed devfolio-v1 policy variant
with strict origin/URL rules, then use the existing CollectorManager transport
for robots, bounded transfers, redirect/DNS controls, raw storage and rate limits.
It must retain enabled, owner/basis/reference, reviewed_at/expires_at, terms_permit,
DISCOVERY_ENABLED and --allow-live gates. Non-curated policy evaluation requires
both source permission and live opt-in. Do not route HTML through Unstop JSON
normalization or enable an adapter by changing only its name.

HTML candidates need a review queue before publication. Keep existing run_due
scheduling, discovery lock, policy-change/expiry rechecks, atomic ingestion,
duplicate/conflict checks and DiscoveryEvidence history. Add offline coverage for
permission/robots/access denials, redirects, review gates, retries and rollback
before adding the adapter to the supported set. No Devfolio source or scheduler
is enabled by this change; approvals.json is unchanged.

## Verification commands

From `.release-local/backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_reviewed_public_import.py tests/test_scraper_ingestion.py tests/test_discovery.py tests/test_discovery_history.py tests/test_event_pagination.py tests/test_events_services.py radar_collector/tests -q
.\.venv\Scripts\python.exe radar_collector/radar_scraper.py --offline-dir radar_collector/fixtures --out radar_collector/output/verified-offline
$env:DEBUG = 'false'
.\.venv\Scripts\python.exe -m workers.import_reviewed_public radar_collector/output/verified-offline/candidates.csv
```

Dry-run expects zero approved and four not-approved rows. Tests override database
settings and store synthetic reviewed records only in disposable test databases.
The shell used for audit had DEBUG=WARN, which is invalid for backend settings;
set DEBUG to a boolean in your command environment rather than changing secrets
or unrelated application configuration.

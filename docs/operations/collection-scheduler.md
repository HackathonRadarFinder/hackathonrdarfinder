# Governed collection scheduling

The one-shot scheduler supplements the existing raw collector. It is disabled by
default, separate from FastAPI, and does not open the application database, ingest
events or send notifications. No approved production source or scraping permission
has been supplied. The existing quotes examples remain unapproved. Do not enable
sources just to obtain a successful run.

This is partial implementation of SRS FR-EVT-01 and SCR-09. It persists per-source
run outcomes and due times, but automatic validated event ingestion, protected
source-manager APIs, audited policy edits, conditional requests, circuit breakers
and transactional downstream workflows require separate reviewed work.

## Approval and configuration

Use an operator-owned schedule JSON file outside source control. The repository's
`backend/modules/2.2-collector/config/schedule.json` has `enabled: false` and no jobs.
To enable a reviewed source, record its existing collector `source_id` and:

- `enabled`: JSON boolean true; each job defaults to false.
- `interval_seconds`: integer from 60 to 604800; high-priority Tier 1 sources must
  use at most 21600 seconds to meet the SRS freshness schedule.
- `adapter_version`: the reviewed collector/parser version. This is operator
  metadata, not an automatically verified artifact signature.
- `approval.owner`, `approval.basis`, `approval.reference`: the real owner, lawful
  basis and reference to actual terms, license or written permission.
- `approval.reviewed_at`, `approval.expires_at`: timezone-aware ISO-8601 timestamps.
  Expired, future-reviewed, incomplete or invalid approval records skip collection.

The top-level file is `{ "enabled": true, "jobs": [...] }`. Referenced sources
must exist in the normal collector configuration. Collection additionally requires
source `enabled: true`, `tos_allows_scraping: true` and a nonempty `tos_note`.
These flags must reflect a human policy review; public accessibility or robots
permission alone does not grant scraping permission. Runtime robots rules still
apply before content and redirect requests. No flags bypass blocked access.

Set only the collector settings in the scheduler's process environment. Configure
a descriptive `COLLECTOR_USER_AGENT` and real `COLLECTOR_CONTACT_EMAIL`. The new
entry point does not load `.env`; keep database/user/SMTP secrets out of collector
processes. Use restricted network egress in any eventual production deployment.

## Reviewed invocation

After source approval and fixture review, a dedicated service timer or scheduler
may invoke the following from the repository root every minute. No OS task,
container service or cluster CronJob is installed by this change:

```powershell
backend/.venv/Scripts/python.exe backend/modules/2.2-collector/schedule.py `
  --config 'C:/approved-config/collection-schedule.json' `
  --sources 'C:/approved-config/collector-sources.json' `
  --state 'C:/collector-state/scheduler.sqlite3' --run
```

The paths above are placeholders. Use a dedicated state location and the same
state database for every invocation. Use one scheduler process for all jobs;
separate state databases would bypass mutual exclusion. The `--run` flag and
top-level enabled boolean are both required. Without either, no state database,
raw storage, logs or requests are created. A zero exit means no technical failure;
inspect aggregate counts and run history to distinguish success, compliant skip
and source blocking. Technical collection failure returns 1; invalid configuration
or state failure returns 2. Nothing treats a compliant refusal as collected data.

## State, recovery and handoff

`source_schedule` stores UTC `next_run_at` and the active source claim.
`collection_runs` stores running/success/skipped/blocked/failed, start/end time,
policy outcome, adapter version, attempts, content type, HTTP status when known,
elapsed milliseconds, raw storage location and successful decoded-content SHA-256.
It stores neither raw content nor exception text. The checksum covers the stored
UTF-8 content, not the original wire bytes. The existing raw snapshots remain
immutable. Normal runs append history and do not delete or rewrite catalog data.

A database lock serializes scheduler invocations and a source claim is committed
before fetching. One invocation shares the existing per-domain rate limiter across
its sequential jobs. Use one scheduled job per origin when setting intervals,
and keep intervals longer than the configured delay; persisted cross-run domain
cooldowns remain a follow-up. Due time advances from run start by the configured
interval even for failed/skipped jobs, avoiding an immediate refusal retry loop.
An expired approval pauses requests by recording a skip; the configuration itself
is never rewritten. Approval is checked at run start and robots is rechecked per
request; scheduling does not continuously revalidate human terms during a job.

A process crash leaves a durable `running` claim and/or `scheduler_lock`. No
automatic lease expiration steals a claim from a potentially active worker. First
stop and join all workers, confirm no collector can resume, reconcile raw snapshot
metadata, preserve a copy of the state, then have an operator mark the interrupted
run failed, clear its matching source claim and clear the singleton lock. Do not
delete the state to clear a failure; that loses schedule and run history. Automated
stale-claim recovery, dead-letter replay, retention and metrics dashboards are not
implemented. Do not run different collector commands concurrently against the
same sources outside this scheduler's lock.

Successful Unstop metadata can be explicitly handed to the existing offline
`workers.ingest_collection` after approval and fixture validation. Do not connect
the standalone unauthenticated source-registry module to production: it uses a
separate SQLite database and its README's claimed collector integration is absent.
Integrate protected source-manager roles, audit and policy metadata on a follow-up
branch before exposing source mutation over the network.

## Verification

```powershell
backend/.venv/Scripts/python.exe -m pytest `
  -c backend/modules/2.2-collector/pytest.ini backend/modules/2.2-collector/tests -q
```

Scheduler tests use temporary SQLite state and the existing loopback-only HTTP
fixture. They exercise double opt-in, due intervals, disabled/unapproved/expired
sources, robots refusals, 403 blocking, bounded 5xx retry, persisted checksums,
overlap/crash claims and secret-safe unexpected errors. No live crawling,
application DB changes, scheduler installation or permission invention occurs.

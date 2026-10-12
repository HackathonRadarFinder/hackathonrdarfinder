# NOTIF-002 integration review

Review date: 2026-10-13 (Asia/Calcutta).

Baseline: `origin/develop` `a67ab0734f50608ec36c928717d33bd6a1dbfd4a`. PR #62 source `origin/feature/NOTIF-002-email-notifications` at `139eb0408a314292a81044bfb50a133a91161480`. Both the six-file merge-base diff and branch-tip differences were inspected; older branch baseline differences were not copied. No applicable AGENTS.md was found in the repository or checked ancestor directories. Work is isolated on `fix/NOTIF-002-email-integration`; existing checkouts and accidental untracked files are preserved.

| PR concern | Integration |
| --- | --- |
| Templates named `remainder`, service loads `reminder` | Actual `registration_reminder.html` and `upcoming_reminder.html` templates are rendered in tests. |
| Unescaped HTML, unchecked URL/header inputs | Autoescaping, StrictUndefined, HTTP(S) validation, credential-free links, safe mailboxes/subjects, multipart text/HTML. |
| Replaced configuration and database credential default | Existing BaseSettings and required database/auth settings retained; validated SMTP fields added, secret password masked. |
| Mock send returns success when unconfigured | Explicit disabled/dry-run modes perform no transport, claims or accepted-state writes. |
| TLS, timeouts and authentication | Certificate/hostname verification, bounded socket timeout, STARTTLS or implicit TLS, optional paired authentication. |
| Incorrect dictionary fields and integer users | Existing User/Hackathon/SavedItem/Preference models and actual UUID/integer IDs used. |
| Process-local logs/deduplication | Dedicated durable delivery table; in-app Notification table remains unchanged. Unique reminder identity and committed conditional claims protect concurrency. |
| Incorrect DELIVERED status | SMTP `accepted` is distinguished from actual delivery; uncertain traffic and crashed claims require operator reconciliation. |
| No worker or scheduling | Dedicated bounded one-shot CLI, explicit consent/ownership, UTC-aware scheduling and bounded retries; no web scheduler or request-handler transport. |
| Failure disclosure | Rendering and transport failures store only safe codes; worker failures emit generic diagnostics. |

Migration `c8d9e0f1a2b3` was reviewed against existing schema and model metadata. It adds one table, foreign keys, uniqueness, due index and state constraints. Event deletion now includes email history in its existing linked-record guard. No existing route, authentication policy, response envelope, preference meaning or collector transaction contract is replaced. Detailed configuration, deployment, recovery and limitations are in `backend/workers/README.md`.

Tests use mocked/forbidden SMTP and disposable foreign-key-enabled SQLite databases. They cover actual templates, escaping, links/headers, configuration validation, disabled modes, TLS/auth/timeouts, refused recipients, safe failures, persistent deduplication, concurrent claims/enqueue/dispatch, retries, reminder timing/timezones, preferences/ownership, existing in-app notifications, actual model compatibility, linked-event deletion and migration upgrade/downgrade with metadata comparison. No real email or development database is used. Validation results are recorded below after final checks.

## Validation

- Full backend suite: **285 passed**, with one existing Starlette TestClient deprecation warning.
- Final focused notification suite: **62 passed**.
- Collector suite: **132 passed**; ingestion/collector implementation was not changed.
- Migration: disposable SQLite upgrade, schema/model metadata comparison and downgrade passed; PostgreSQL offline DDL generation passed without connecting to a database. Live PostgreSQL concurrency and provider integration remain deployment checks.
- Syntax compilation of application, workers, tests and migrations passed. `.venv` dependency check reported no broken requirements; Jinja2 3.1.6 is the only added direct dependency. Whitespace/diff checks passed.
- The first focused attempt encountered a missing disposable-temp parent and exposed SMTP exception inheritance classification; both were corrected. The first full run found the old hardcoded Alembic head assertion; it was updated to the new head and strengthened with delivery-table upgrade/downgrade checks. No auth or migration assertion was removed.
- Rendering/SMTP tests forbid real transport; CLI disabled/dry-run tests verify that even a database file is not opened/created. Crash-after-acceptance testing verifies a durable `sending` claim is not automatically retried when recording the outcome fails.

There is no exactly-once SMTP guarantee, confirmed-delivery callback, automatic stale-claim rescue, preference UI/API, or retention purge. Opt-in consent and historical UTC interpretation need operational care. Disabled/dry-run are explicit no-op modes rather than fake successes. See the worker guide for deployment and manual ambiguity reconciliation. No push, merge, PR closure, intern-branch modification, live migration or real email is part of this integration.

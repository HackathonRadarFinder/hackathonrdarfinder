# Email reminder worker

Run from `backend` with the project `.venv` interpreter:

```powershell
python -m alembic upgrade head
python -m workers.email_reminders --batch-size 100
```

Apply migration `c8d9e0f1a2b3` after `b7c8d9e0f1a2` using the normal reviewed deployment process, before enabling the worker. It adds only `email_deliveries`, its due index, reminder uniqueness constraint, status/kind/attempt checks and foreign keys to existing users/events. It leaves in-app `notifications`, preferences, models and earlier migrations intact. Downgrade drops email state: stop all email workers first; doing so loses deduplication history and can cause repeated reminders after re-upgrade. Do not downgrade a live queue without an export/recovery plan.

Use a dedicated cron job, service timer, or Kubernetes CronJob every five minutes. Do not import a scheduler into FastAPI startup, dispatch from request handlers, or use a separate scheduler in every web process. Each invocation exits after bounded enqueue and dispatch batches (1–1000 each; default 100). Multiple invocations use the same durable queue and conditional claim; PostgreSQL unique constraints protect enqueue races. SQLite enqueue transactions are serialized. High-volume production should use PostgreSQL and monitor backlog age.

## Configuration

Existing `DATABASE_URL`, authentication, logging and application settings are unchanged; no credential-bearing database default is added. Supply SMTP credentials through the deployment secret mechanism, never commit `.env` or passwords.

| Setting | Meaning |
| --- | --- |
| `EMAIL_MODE` | `disabled` by default; `dry-run` explicitly prevents network, claims and successful-send records; `enabled` permits dispatch. Disabled/dry-run CLI invocations are no-ops reporting mode and zero queue/acceptance counts, not rendered previews. |
| `SMTP_HOST` | Required when enabled; no implicit localhost bypass. |
| `SMTP_PORT` | 1–65535; default 587. Use 465 for typical implicit TLS providers. |
| `SMTP_TLS` | `starttls` (default) or `implicit`. Both verify certificates and hostnames with system trust; plaintext/insecure TLS is unsupported. |
| `SMTP_TIMEOUT` | Socket timeout, greater than 0 and at most 60 seconds; default 10. It is not a hard overall batch deadline. |
| `SMTP_USERNAME`, `SMTP_PASSWORD` | Optional together for authenticated relays. Empty together supports a trusted relay without login; TLS still applies. Password uses `SecretStr`. |
| `EMAIL_FROM` | Validated sender mailbox; default `noreply@example.com` is a placeholder. Set an address approved by the SMTP provider. |

## Consent, recipients and timing

The worker joins actual `SavedItem.user_id`/`hackathon_id`, UUID `User.id`, integer `Hackathon.id`, `User.name/email/status`, and `Hackathon.title/url/registration_deadline/start_date`. Only active users with a saved event and their own `Preference(key='email_reminders', value='true')` qualify. Missing global consent means no email. Optional `email_registration_reminders` and `email_upcoming_reminders` keys can independently disable kinds; when present, only exact `true` enables that kind. Other preference keys are left untouched.

No new preference or log API is exposed. Existing notification readiness behavior remains unchanged. Set consent only through trusted user-owned preference management; this change does not introduce an opt-in UI or self-service preference API. Do not bulk opt users in without consent. The worker checks ownership, consent, active status and current event timing again immediately before transport. A consent/event change racing after this check cannot retract SMTP traffic already underway.

Registration and upcoming reminders are queued when their timestamp is in `(now, now + 24 hours]`. Event timestamps use existing UTC-naive database storage; the CLI uses aware UTC and rechecks a live clock before each send. Service calls reject naive worker times. Historical offsetless event data is assumed UTC; nothing rewrites existing dates. Registration reminders are queued first. The worker cancels already-expired reminders before transport, although SMTP can finish after an event time passes. A changed event timestamp creates a new deduplication identity; old queued reminders are cancelled on recheck. Unchanged timestamp reminders are never enqueued again, even if their outcome was failed/cancelled.

## Outcomes and retries

`pending` → atomic committed `sending` claim → `accepted`, `retry`, `failed`, `cancelled`, or `unknown`. Unsent disabled/dry-run work never becomes accepted. HTML templates autoescape user/event fields, links must be HTTP(S) without credentials, and subjects/mailboxes reject header controls. Both plain text and HTML are included.

`accepted` means SMTP accepted the message for its recipient, not that the mailbox received it. There are no provider delivery/bounce callbacks, delivery receipts or confirmed-delivery claims. A QUIT failure after a known acceptance retains acceptance. Recipient refusal or a negative SMTP response is eligible for a retry after five minutes, then ten minutes, up to three attempts total and never beyond event time. Even permanent/authentication rejections currently consume this bounded retry budget. Rendering/validation failures are terminal and store only `render_error`. Transport diagnostics store safe codes, never exception text, SQL, recipient content or credentials. The CLI reports aggregate outcomes; database failures exit nonzero with a generic message and session closure rolls back uncommitted work.

## Crash ambiguity and recovery

There is **no exactly-once delivery guarantee**. SMTP can accept DATA immediately before a disconnect or a process/database crash prevents recording acceptance. Ambiguous transport outcomes become `unknown`. A crash after claim can leave `sending`; neither state is automatically reclaimed, so a slow worker cannot overlap a lease-based retry. This chooses possible missed mail over automatic duplicate sends for uncertain outcomes.

Monitor counts/age of `pending`, `retry`, `sending`, `unknown`, `failed`, and `accepted`, plus worker nonzero exits. For stale `sending`, first stop/join the owning worker and confirm it cannot resume. Reconcile with SMTP/provider logs using recipient, event, claim time and operational records. If acceptance is confirmed, set `accepted` and its acceptance timestamp. If nonacceptance is confirmed, an operator may reset to `retry` with an appropriate future `next_attempt_at`, preserving attempts (maximum three). If evidence is unavailable, leave `unknown` or cancel; explicitly accept duplicate risk before manually retrying. Never blindly reset active `sending` rows. No automated stale-claim rescue or retention purge is included.

Email history protects event deletion through the existing related-record 409 contract. Retention/deletion policy for this new history and user account deletion requires separate review. TLS/provider configuration and PostgreSQL concurrency need deployment verification; local tests use only mocked SMTP and disposable SQLite databases.

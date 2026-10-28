# Complete live frontend, account reminders and catalog predictions

The default application previously lacked an integrated live user journey.
This change preserves the existing frontend design as a labelled `/demo` and
connects the live application to backend authentication, searchable paginated
catalog, event details, organizations and backend-authorized administration.
Users can save events to their own account and explicitly consent to reminder
emails through APIs backed by the existing tables and reminder worker.

Catalog predictions use distinct past database dates with the existing baseline
model. Estimates advance to the next future recurrence; confidence is explicitly
labelled heuristic and insufficient history produces no estimated date.
An offline worker connects stored collector metadata to transactional ingestion,
and the backend image includes collector dependencies, ingestion and email workers.
No migration or existing response envelope is changed; search adds optional `q`.

Validation: 288 backend tests, 132 collector tests, 31 deployment safeguard tests,
16 frontend tests including the disposable HTTP contract journey; all passed.
Frontend lint/build, dependency consistency and four rendered overlays passed.
No real SMTP traffic or production database operations were performed.

Before release: verify container builds/disposable PostgreSQL in CI, browser
interaction in staging, approved live collection and scheduled jobs, and real
mailbox receipt at an approved safe destination. Docker engine and browser
automation were unavailable locally. See `final-integration.md` for exact commands
and the acceptance checklist.

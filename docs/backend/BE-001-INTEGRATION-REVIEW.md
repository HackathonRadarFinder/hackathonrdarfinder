# BE-001 Events API and Backend Services integration review

Review date: 2026-10-11 (Asia/Calcutta).

The corrected integration preserves the existing Events and Organizations API contracts, moves database work into reusable services, and restricts mutations and new administrative operations through the existing AUTH-001 administrator dependency. It is prepared on `fix/BE-001-events-api-integration` for review against `develop`.

## Scope and Git state

- Baseline: `origin/develop` at `8e2e70aaaa1afd4bb99114ac976f1b2db744c8fd`, containing merged AUTH-001 PR #74 and OPS-001 PR #75. Authenticated GitHub inspection confirmed the same current `develop` SHA.
- Original work: [PR #66](https://github.com/HackathonRadarFinder/hackathonrdarfinder/pull/66), `features/BE-001-events-api`, head `1a0237bd6baf5255e7f85857e9b0493343599a02`.
- Integration method: manual adaptation of the original eight-file change onto current `develop`; no Git merge was performed and no merge is in progress.
- Thirteen integration files are modified or newly created, including this report. All integration changes are unstaged at the time of this report.
- The original intern branch and `develop` were not modified. No commit, push, PR creation, deployment, or real database migration was performed.
- The unrelated untracked `-files -u` file is preserved and excluded from the staging commands below. Existing development databases, AI model artifacts, frontend dependencies, ignored files, and secrets are outside the change.

## Findings in the eight original PR files

The original PR diff contains eight files, 410 insertions and 174 deletions. Comparing entire branch tips also shows older baseline differences; those must not be mistaken for changes authored by PR #66.

| Original file | Finding | Corrected integration |
| --- | --- | --- |
| `backend/app/api/routes/events.py` | Removed the existing `{message, data}` envelopes, replaced the legacy organization-name input, and left event mutations public. Large deletions moved code into services but also changed the external contract. | Preserves all five URLs, success envelopes, messages, and existing success status codes; uses typed responses, validated integer IDs, and `require_admin` for POST/PUT/DELETE. |
| `backend/app/api/routes/organizations.py` | Detail/create/update changed to bare objects while list retained an envelope; writes remained public. | Restores the consistent existing envelopes and applies the existing administrator guard to writes. |
| `backend/app/api/routes/admin.py` | Added six unguarded administrative operations. `/admin/users` returned raw User ORM objects, potentially exposing password hashes. | Guards all six added operations, uses explicit response schemas and safe user field projection, and preserves the existing public readiness endpoint. |
| `backend/app/core/errors.py` | Added an unused error system that subclasses `HTTPException` with a nested dictionary. The current global handler would stringify that dictionary instead of returning its intended structure. | Does not introduce this file. Reuses existing `HTTPException`, `AppException`, global handlers, and `app/schemas/errors.py`. |
| `backend/app/schemas/event.py` | Replaced validated URLs with unrestricted strings, accepted blank/oversized titles, and allowed unchecked or absent organization references. | Validates write fields against existing column limits, retains legacy organization-name input, adds positive integer organization IDs, verifies exactly one reference, and separates tolerant read schemas from strict write validation. |
| `backend/app/services/admin_service.py` | Returned raw users and duplicated deletion code without rollback or relationship checks. | Projects safe user fields with eagerly loaded roles and delegates deletions to the shared event/organization services. |
| `backend/app/services/event_service.py` | Did not verify referenced organizations, translate database failures, roll back failed transactions, or protect related predictions/versions/saved items on deletion. | Resolves the organization, centralizes database error handling, protects related rows, and shares the same deletion behavior with admin routes. |
| `backend/app/services/organization_service.py` | Duplicate-name updates could fail unexpectedly; commit failures lacked rollback; organization deletion ignored referencing events. | Checks duplicate creates/renames, handles constraint races, rolls back database errors, and rejects deletion while events reference an organization. |

## Corrected file inventory

| File | Purpose |
| --- | --- |
| `backend/app/api/routes/events.py` | Existing event URLs/envelopes, administrator write authorization, typed responses. |
| `backend/app/api/routes/organizations.py` | Existing organization URLs/envelopes, administrator write authorization, typed responses. |
| `backend/app/api/routes/admin.py` | Six protected admin operations and preserved public status endpoint. |
| `backend/app/schemas/event.py` | Validated event writes, legacy organization input, safe response projection, UTC datetime normalization. |
| `backend/app/schemas/organization.py` | Organization write validation and tolerant historical-row responses. |
| `backend/app/schemas/admin.py` | Explicit admin statistics and user response fields. |
| `backend/app/schemas/responses.py` | Shared success envelopes, integer path IDs, references to the existing error schema. |
| `backend/app/services/event_service.py` | Event CRUD and relationship validation. |
| `backend/app/services/organization_service.py` | Organization CRUD, uniqueness and relationship validation. |
| `backend/app/services/admin_service.py` | Administrative reads, safe user projection and shared deletion wrappers. |
| `backend/app/services/database.py` | Common rollback and safe database exception translation. |
| `backend/tests/test_events_services.py` | Isolated API, authorization, integrity, transaction and regression coverage. |
| `docs/backend/BE-001-INTEGRATION-REVIEW.md` | Findings, validation evidence, compatibility notes and finalization instructions. |

No dependency, SQLAlchemy model, Alembic migration, AUTH implementation, prediction implementation, notification implementation, scraper implementation, frontend, or OPS workflow change is required.

## API contracts and endpoint inventory

Existing event and organization success responses retain `{ "message": "...", "data": ... }`; deletion responses retain `{ "message": "..." }`. Existing POST/PUT/DELETE success codes remain 200. PUT remains a full replacement, so omitted optional fields are reset to null.

| Endpoints | Access | Status |
| --- | --- | --- |
| `GET /events/`, `GET /events/{event_id}` | Public | Preserved. |
| `POST /events/`, `PUT /events/{event_id}`, `DELETE /events/{event_id}` | Active administrator with valid, nonrevoked access token | Preserved URLs; previously public mutations now require authorization. |
| `GET /organizations/`, `GET /organizations/{organization_id}` | Public | Preserved. |
| `POST /organizations/`, `PUT /organizations/{organization_id}`, `DELETE /organizations/{organization_id}` | Active administrator with valid, nonrevoked access token | Preserved URLs; previously public mutations now require authorization. |
| `GET /admin/status` | Public | Preserved readiness response. |
| `GET /admin/stats` | Administrator | Added; returns `total_events`, `total_organizations`, `total_users`. |
| `GET /admin/events`, `GET /admin/organizations`, `GET /admin/users` | Administrator | Added; returns `{ "data": [...] }`. |
| `DELETE /admin/events/{event_id}`, `DELETE /admin/organizations/{organization_id}` | Administrator | Added; uses the same guarded deletion services as the public-path counterparts. |
| Existing `/auth/*`, `/predictions/*`, `/notifications/`, `/health`, `/api/v1/health` | Existing access policy | Preserved; implementations unchanged. |

No existing endpoint was removed. Event writes accept either the existing `organization` name or the new `organization_id`, exactly one per request. Unknown organizations return 404. Numeric identifiers must be positive and fit the current signed 32-bit database integer columns. Body organization IDs must be JSON integers, not booleans or numeric strings.

Title and organization name are trimmed and must be nonempty and at most 255 characters. Optional bounded fields match existing database column sizes. New URLs must be HTTP(S) and fit the 500-character columns. Response schemas retain plain strings for historical URLs so older scraped rows do not become unreadable. Offset-bearing event dates are normalized to UTC before storage in the existing timezone-naive columns; end dates cannot precede start dates. Out-of-range UTC conversion is a validation error rather than an uncaught overflow.

## Authentication and authorization

All protected routes use the existing `require_admin` dependency. It checks the signed JWT, expiration, token type and identifier, database-backed revocation, active user status, and current database roles. No client-supplied role grants permission. Existing UUID identities, password handling, self-registration restrictions and persistent logout remain unchanged.

The default write policy is administrator-only. The six other existing roles receive 403 for mutations and administrative reads; granting a reviewer, source manager, or institution coordinator additional permissions requires an explicit business policy. Public reads and `/admin/status` remain public.

Admin user output is limited to `id`, `name`, `email`, `status`, `created_at`, and role names. Password hashes and other ORM attributes are excluded from both the selected user columns and the serialized response.

Verification status: **Passed** in the full 115-test backend run, including the existing AUTH regressions and the new protected-route permission matrix.

## Database compatibility, transactions and errors

The integration uses the existing `Hackathon`, `Organization`, `User`, `Role`, and dependent models and the existing session dependency. Event/organization IDs remain integers and user IDs remain UUIDs. There are no duplicate models, table changes, or new migrations. Existing migration history remains `e5a6b09ae2ec` followed by `b7c8d9e0f1a2`.

- Creating or updating an event verifies the referenced organization before changing the row.
- Duplicate organization creates and renames return 400, preserving the established duplicate-create status. Constraint failures after a preflight check are also translated and rolled back.
- Deleting an organization referenced by events returns 409.
- Deleting an event referenced by `EventVersion`, `Prediction`, or `SavedItem` returns 409. Related records are not silently deleted.
- Database integrity failures return a safe 400/409 message. Other SQLAlchemy failures are rolled back and return a generic 503 `DATABASE_ERROR`, without SQL, credentials or database parameters in the response.
- The existing global error shape remains `{code, message, details, request_id, timestamp}` and preserves request IDs. OpenAPI refers to the existing shared error schema instead of introducing another format.

New tests create disposable SQLite databases with foreign keys enabled and override `get_db`. Existing AUTH test configuration also forces isolated test settings. No verification should connect to the developer's database or read credentials into command output.

Migration/model compatibility verification: **Passed**. An isolated temporary database upgraded to `b7c8d9e0f1a2`; Alembic `compare_metadata` reported no differences. SQLAlchemy mapper validation covered 14 tables. The existing AUTH suite also exercises an isolated migration round trip.

## GitHub evidence

Authenticated, read-only GitHub API inspection returned the following snapshot. Credentials were obtained through the existing Git credential helper, retained in memory, and neither saved nor printed.

| Item | PR #66 | PR #73 |
| --- | --- | --- |
| Link | [Events API and Backend Services](https://github.com/HackathonRadarFinder/hackathonrdarfinder/pull/66) | [Event Pagination, Filtering, and Error Schemas](https://github.com/HackathonRadarFinder/hackathonrdarfinder/pull/73) |
| Source head | `1a0237bd6baf5255e7f85857e9b0493343599a02` | `c46e1c23ba79786d0d2b3c3c7c207f8f11db003c` |
| State | Open, non-draft, mergeable, `clean` | Open, non-draft, mergeable, `clean` |
| Source-head checks/statuses | None returned | None returned |
| Synthetic merge checks | None returned | None returned |
| Head/branch workflow runs | None returned | None returned |

Synthetic merge SHAs inspected were `a2ad9a8df949bac846aae3939024b88fb364ee4a` for PR #66 and `9e2a7746fbbb216e981048ffed4ba2e9d9659a5b` for PR #73. There were no recorded failure logs to diagnose for these PR heads. The combined-status endpoint reported `pending` with an empty statuses array; that is not evidence of a running CI job. GitHub's clean mergeability state is also not evidence of successful tests.

Remote checks for this corrected integration remain pending its approved publication and PR review. The existing CI workflow runs on pull requests targeting `develop`/`main` and pushes to those branches; pushing this new feature branch alone does not trigger its required checks. No PR was created automatically.

## Validation results

| Check | Actual result |
| --- | --- |
| Full backend pytest suite | **115 passed, 0 failed, 1 warning, no skips**, 39.03 seconds. |
| BE-001 API/service tests | **76 passed**, included in the full backend run. |
| Existing AUTH/API regressions | **39 existing backend tests passed**, including AUTH-001 and its isolated migration round trip. |
| Python syntax/import validation | **Passed**: 40 application files and 6 test files. |
| Application startup, route inventory and OpenAPI/schema inspection | **Passed**: TestClient startup and 26 OpenAPI paths. |
| SQLAlchemy model and isolated Alembic verification | **Passed**: 14 mapped tables; temporary database upgrade to `b7c8d9e0f1a2`; no `compare_metadata` differences. |
| `pip check` | **Passed**. |
| OPS infrastructure validation | **Passed**: four rendered overlays with nine resources each, workflow pins/guards and YAML checks. |
| Operations tests | **31 passed**, 2.99 seconds. |
| Actionlint | **Passed**, version 1.7.7; optional ShellCheck was unavailable locally. |
| Final production code review | **Passed**; no additional material production defect identified after the datetime correction. Final whitespace/scope check is recorded below. |
| PostgreSQL-specific execution, Docker builds and frontend checks | Not run locally for this backend-only change; required remote CI remains pending. |
| Live deployment or development-database migration | Not performed. |
| Corrected integration remote CI | Not run before approved commit/push and PR publication. |

The warning is the existing Starlette deprecation of its httpx-based TestClient; dependency versions were not changed.

The first sandbox test attempt encountered 69 setup `PermissionError` failures because pytest could not access its temporary directory. An approved rerun passed those 69 tests, and the expanded final backend suite subsequently passed all 115 tests. Those initial setup failures were an execution-environment issue, not ignored application failures.

The new suite exercises public retrieval; administrator CRUD; legacy names and integer organization references; missing and invalid IDs; validation; all nonadministrator roles; missing/malformed/expired/revoked tokens; inactive and demoted users; safe admin users; uniqueness races; preserved foreign-key dependents; commit/read failure rollback; health/request IDs; and prediction/notification route regressions. Prediction regression tests stub predictor functions to exercise routing without modifying or loading real AI artifacts. The separate unchanged source-registry application was not executed because its imports use a hardcoded `sources.db`; no claim of testing that application is made.

Final whitespace/scope review: **Passed**. Reviewed all 13 integration files against `origin/develop`, including new files. `git diff --check` and explicit whitespace checks passed; the index remains empty. AUTH, OPS, models, migrations, dependencies, frontend and other module paths have no tracked diff. The unrelated untracked `-files -u` remains untouched.

## Reproduce local validation

Run from the repository root. Backend tests set isolated settings before application import and override database sessions; do not run Alembic directly using local development settings.

```powershell
Push-Location backend
.\.venv\Scripts\python.exe -m pytest tests -q
.\.venv\Scripts\python.exe -m pip check
Pop-Location
.\backend\.venv\Scripts\python.exe -m pytest tests/operations -q
.\backend\.venv\Scripts\python.exe scripts/validate_ops.py
.\backend\.venv\Scripts\python.exe scripts/run_actionlint.py
```

## PR #73 compatibility plan

PR #73 builds on PR #66 and adds pagination/filtering changes in only `events.py`, `schemas/event.py`, and `services/event_service.py`. Its current branch includes the original unsafe service implementations and must be adapted after this corrected baseline is integrated.

1. Rebase or otherwise prepare PR #73 against the corrected `develop` with the author's approval; do not replace the integration's authorization, organization resolution, transaction handling, deletion guards, or write schemas with the old branch versions.
2. Retain the pagination/filter feature work: `page`, bounded `page_size`, location/mode filters, organization ID filter, filtered total count, and deterministic ID ordering. This integration deliberately does not duplicate those features.
3. Resolve the response contract explicitly. PR #73 proposes `{items, total, page, page_size}`, whereas existing clients use `{message, data}`. Preserve the legacy envelope or introduce a documented versioned/opt-in contract with tests; do not silently replace it.
4. Reuse `app.schemas.errors.ErrorResponse`. PR #73's local `detail: str` error schema does not describe the current global error envelope and should not be restored.
5. Keep the existing service entry points and replace only listing-query behavior as needed. In particular, do not restore `Hackathon(**event.model_dump())`: this integration also accepts the legacy `organization` name and resolves it into an existing organization ID before constructing a database model.
6. Retest writes, RBAC, revocation, input validation, error responses and relationships after pagination changes. Add pagination/filter-specific tests in PR #73.

## Remaining limitations and recommendation

- Runtime SQLite connections currently do not explicitly enable `PRAGMA foreign_keys`; the isolated tests do. Application preflight checks protect ordinary deletion/reference operations, but race protection ultimately requires database-enforced constraints. Production uses PostgreSQL, where the existing foreign keys are enforced. Enabling SQLite foreign keys for all runtime connections would require separate compatibility consideration for existing data and is not silently applied to the development database here.
- Event, organization and admin lists remain unpaginated. Pagination/filtering belongs to PR #73; large collections can still consume substantial memory and bandwidth.
- Writes have no idempotency key or optimistic concurrency mechanism. A connection/refresh failure after a successful commit can return an error even though the write persisted; blindly retrying a create can duplicate an event. Concurrent full replacements remain last-write-wins.
- Administrator-only mutation is intentionally conservative. Broader role permissions and ownership rules remain a business-policy decision.
- Stricter write validation may reject historical input previously accepted, while existing rows remain readable. Date normalization assumes offsetless input already represents the stored timezone convention; no historical rows are rewritten.
- Local SQLite tests do not replace PostgreSQL-specific execution. Remote CI must verify its disposable PostgreSQL migration step and all required checks; deployment and recovery validation remain separate operations work.

Recommendation for the original PR #66: **REQUEST CHANGES** because its unguarded mutations/admin reads, potential password-hash exposure, contract changes, and transaction/integrity gaps are material. Recommendation for the corrected integration: **APPROVE for GitHub review**, with successful required remote CI still required before merge. No merge approval is implied by the local test results.

## Corrected PR draft

Title: **fix(be): integrate Events API services with AUTH-001 authorization and preserved contracts**

Body:

> PR #66 introduced reusable event, organization and admin services but exposed privileged operations, changed existing success envelopes, and omitted transaction and relationship safeguards. This integration preserves the established URLs and `{message, data}` contracts, uses the existing administrator dependency for writes and new admin reads, safely projects users, and handles database failures and referenced-record deletion through shared services.
>
> The change supports the legacy organization-name event input and validated integer organization IDs, retains all AUTH-001 and OPS-001 implementations, and makes no database/model/migration or dependency changes. Pagination/filtering remains in PR #73, whose response/error contracts must be adapted to this baseline.
>
> Validation: 115 backend tests and 31 operations tests passed. Dependency consistency, syntax/imports, application startup/OpenAPI, 14 mapped tables, isolated migration/schema comparison, four infrastructure overlays and actionlint passed. ShellCheck was unavailable locally. All database-backed local tests use isolated databases with dependency overrides. Real databases, AI artifacts, frontend dependencies and unrelated local work were preserved. Remote CI remains required before merge.

## Finalization commands — only after explicit approval

Run from the repository root after reviewing the final test results. These commands stage only the 13 integration paths and deliberately exclude the unrelated `-files -u` file. There is no pending merge to complete; do not run `git merge --continue`. If the branch or worktree has changed since this review, inspect the new state first.

```powershell
git branch --show-current
git status --short
git ls-files -u
git diff --check

$be001Files = @(
    'backend/app/api/routes/admin.py'
    'backend/app/api/routes/events.py'
    'backend/app/api/routes/organizations.py'
    'backend/app/schemas/admin.py'
    'backend/app/schemas/event.py'
    'backend/app/schemas/organization.py'
    'backend/app/schemas/responses.py'
    'backend/app/services/admin_service.py'
    'backend/app/services/database.py'
    'backend/app/services/event_service.py'
    'backend/app/services/organization_service.py'
    'backend/tests/test_events_services.py'
    'docs/backend/BE-001-INTEGRATION-REVIEW.md'
)
git add -- $be001Files
git diff --cached --check
git diff --cached origin/develop --stat
git diff --cached origin/develop
git status --short
git commit -m "fix(be): integrate secure Events API and backend services"
git push -u origin fix/BE-001-events-api-integration
```

Creating a corrected PR and merging it require separate user authorization. Use the draft above against `develop` after approved publication, and require successful remote backend, frontend, infrastructure and Docker checks before integration.

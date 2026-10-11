# AUTH-001 integration review

Backend authentication is ready for code review. The current branch remains
`fix/AUTH-001-integration`; the merge of `origin/develop` is still pending.
No index entries, commits, branches, remotes, development databases, AI artifacts,
or frontend dependencies were changed by this task.

## Changes made in this task

- `app/api/deps.py`: query database revocations on every authenticated request;
  validate expiration type and bounded token identifiers; carry expiration in
  the validated token payload. Database failures do not bypass authentication.
- `app/api/routes/auth.py`: commit revocation before reporting logout success;
  record only JTI and expiration, with a database timestamp; handle concurrent
  duplicate inserts after rollback and verification of the existing record.
- `app/schemas/user.py`: require JTI and expiration in internal token payloads.
- `database/migrations/versions/b7c8d9e0f1a2_persistent_token_revocation.py`:
  create `revoked_tokens`, descending from `e5a6b09ae2ec`.
- `tests/conftest.py`: force test-only database, signing key, and DEBUG settings
  before application imports, independent of the development `.env`.
- `tests/test_auth.py`: use an isolated temporary file database per test so
  persistence can be checked across fresh connections.
- `tests/test_auth_revocation.py`: add persistence, malformed JWT, seven-role
  RBAC, duplicate logout, endpoint preservation, and migration round-trip tests.
- This report.

The existing untracked `app/models/revoked_token.py` and its existing import in
`app/models/__init__.py` were reused without changes. No duplicate User or Role
models were introduced. Existing security, registration, password-length,
dependency, and authentication-test changes were preserved.

## Validation

From `backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q --tb=short
.\.venv\Scripts\python.exe -m pip check
```

Final result: **38 passed in 26.10 seconds**, with three deprecation warnings
(Starlette's httpx integration and existing class-based Pydantic configuration
in hackathon/organization schemas). `pip check`: no broken requirements.
Installed PyJWT, bcrypt, email-validator, SQLAlchemy and Alembic versions match
the declared pins; no dependency installations or manifest changes were needed.

Migration tests execute Alembic upgrade, downgrade to `e5a6b09ae2ec`, and upgrade
again in a fresh temporary SQLite database. The persistence test clears module
state and disposes pooled connections before checking the revoked token again.
It also proves another token for the same user remains valid. Existing inactive
account and database role-change tests pass. All seven roles are checked against
all four exposed RBAC demonstration endpoints, including misleading signed role
claims. Existing event and organization reads, predictions status, notifications,
admin status, and both health endpoints remain accessible.

The source-registry module's separate suite was not run: its application import
calls `create_all` against a hardcoded relative `sources.db`. That requires a
separate isolated working-directory setup to avoid touching its existing DB.
Prediction inference/training and frontend behavior were not exercised.

## Remaining limitations and review findings

- Deploy this migration before deploying the new authentication code. No
  migration was run against the development database. PostgreSQL execution and
  a real multi-worker deployment have not been tested; SQLite persistence was.
- Every protected request now requires a database lookup. Database outages fail
  closed, but currently surface as generic 500 errors.
- Logout revokes one access token. Other sessions remain active, and a request
  already authenticated before logout commits can still finish. Reusing an
  already revoked token for logout returns 401. There is no logout-all flow.
- Expired revocation records are retained. A scheduled cleanup may delete them
  only after expiration; no cleanup job is included here.
- Existing event/organization writes and prediction routes have no RBAC guards;
  admin status and notifications are public placeholders. Those routes were
  preserved as requested. Authentication guards must be adopted by module owners
  before describing the entire API as access-controlled.
- Frontend `src/services/authService.js` still mocks registration/login/logout.
  End-to-end frontend authentication integration remains separate work.
- Login throttling, refresh-token rotation, password reset, email verification,
  and issuer/audience scoping are not implemented in the current auth flow.
- The existing global HTTP exception handler drops exception headers, including
  the Bearer challenge; this does not bypass authentication but affects protocol
  responses. It was left intact to preserve the shared error-handling module.
- The incoming staged AI, source-registry, frontend, Docker, and documentation
  changes are outside AUTH-001 and were preserved. Compared with local
  `origin/develop`, tracked differences are concentrated in authentication,
  configuration, `.env.example`, requirements and tests. New untracked files
  are absent from ordinary `git diff` until explicitly staged.
- A source-registry `sources.db` binary is already staged by the merge; verify
  whether the project intends to track it. It was not read, modified or removed.
- Full diff checks find pre-existing whitespace warnings in INTERN_SETUP,
  neural model, initial migration, source router, frontend CSS, and auth service.
  The files edited by this task pass targeted whitespace checks. No unrelated
  formatting cleanup was performed.

## Finalize the merge only after approval

The following commands are provided for review; they have **not** been executed.
Run from the repository root. Existing incoming merge changes are already staged.
Explicit paths capture the outstanding AUTH work without sweeping in secrets or
other untracked files.

```powershell
git status --short
git ls-files -u
git add -- backend/app/api/deps.py backend/app/api/routes/auth.py backend/app/core/security.py backend/app/models/__init__.py backend/app/models/revoked_token.py backend/app/schemas/user.py backend/app/services/auth_service.py backend/requirements.txt backend/tests/test_auth.py backend/tests/conftest.py backend/tests/test_auth_revocation.py backend/database/migrations/versions/b7c8d9e0f1a2_persistent_token_revocation.py backend/AUTH-001-REVIEW.md
git diff --cached --stat
git diff --cached --check
git diff --cached -- backend/app/api/deps.py backend/app/api/routes/auth.py backend/app/models/revoked_token.py backend/database/migrations/versions/b7c8d9e0f1a2_persistent_token_revocation.py backend/tests/conftest.py backend/tests/test_auth_revocation.py
git commit -m "Merge origin/develop and complete AUTH-001 persistent JWT logout"
git status --short
```

Review the complete staged merge, including the pre-existing whitespace warnings
and tracked DB, before committing. The commit concludes the pending merge.
Pushing, switching branches, opening a PR, and deploying migrations are separate
actions requiring your approval; no force push is necessary.

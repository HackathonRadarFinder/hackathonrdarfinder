# Railway / Cloudflare deployment checkpoint - 2026-10-29

Implemented and locally verified on
`feat/railway-cloudflare-production-deployment`, based on main
`ee13ff79e6e2bce22e537df38e1965dc0bb455f1`. Target integration branch: `develop`.
This is **not a deployed release**. No public URL or provider resource is claimed.

| Component | Status | Evidence | Remaining blocker |
| --- | --- | --- | --- |
| Railway project | Not provisioned | No confirmed account/project connection | Railway authorization and GitHub integration |
| PostgreSQL | Disposable verification passed | 13 tests, owned PostgreSQL 16, zero failures/skips | Private Railway instance, volume and backups |
| Backend | Built and locally verified | Readiness/catalog API and non-root UID 10001 | Railway staging deployment |
| Frontend | Built and locally verified | Nginx/React browser checks, custom DNS upstream, UID 101 | Railway staging domain |
| Collector | Bootstrap verified; live acquisition disabled | Root-owned temporary mount initialized, privileges dropped, disabled worker returned safely | Railway persistent volume and authorized Brabble key/source policy |
| Database migrations | Locally verified | New release command migrated empty disposable DB to head; advisory lock tests cover failure cleanup | Configure backend pre-deploy phase |
| Cloudflare DNS | Unchanged | No DNS records invented or edited | Authorized zone and owner-confirmed hostname |
| HTTPS | Unverified externally | No provider URL exists | Actual Railway/domain certificate verification |
| Authentication | Isolated API journey passed | Register/login, saved items, role denials, logout revocation | Public-domain session smoke test |
| Hackathon catalog | Isolated API/browser journey passed | Review/publication, pagination, detail, attribution, deduplication | Reviewed production import and public smoke test |
| University directory | Existing implementation preserved | No institution code, imports or database records changed | Railway data import approval and public query verification |
| GitHub CI/CD | Existing CI reused | PR workflow already targets develop/main; Docker acceptance extended | PR CI result; provider Wait for CI and branch governance settings |
| Public deployment | Blocked externally | No real deployment/domain link | Provider access and staging verification |

## Verification

- Initial focused tests: 7 passed; included again in the Linux regression pass.
- Linux image regressions: **87 passed**, covering Railway URL/lock configuration,
  notifications, production Compose configuration and discovery.
- Owned PostgreSQL acceptance: **13 passed**, zero failures/errors/skips. Includes
  fresh migrations, schema/ORM agreement, transactional imports, concurrency,
  explicit review/publication, role denials, personalization, saved records,
  notifications, SMTP suppression and public ML suppression.
- Built-image browser acceptance passed: reviewed catalog, pagination, detail,
  unknown deadline and linked source attribution; zero browser errors.
- Collector mount initialization, UID drop and disabled/no-network execution passed.
- Default Compose Nginx configuration passed `nginx -t`; unsafe upstream host
  input was rejected; custom upstream proxy requests and `no-store` header passed.
- Backend/frontend images built. First backend attempt stopped at a Docker Hub
  metadata timeout; one retry succeeded. No repeated successful builds.
- Python compile checks and `git diff --check` passed.
- Existing Starlette/httpx deprecation warning remains; no SMTP delivery is claimed.
- First Windows acceptance/regression attempts were stopped before database writes
  because scientific-library imports stalled. The first owned container was removed;
  the subsequent Linux-image acceptance passed. No existing database was modified.

Ignored evidence: `.test-support/railway-acceptance-linux/postgres_report.json`,
`postgres-tests.xml`, `complete-release-journey.json`, and
`container-browser/report.json` within that directory. The successful run was
`7c66fbb26cdc`; all three owned named test containers were removed, and no
persistent volumes were deleted. Collector and test subprocess containers used
automatic removal. Evidence contains synthetic owned test data, not source permissions.

Reproduction:

```powershell
docker build -t radar-backend:railway-check ./backend
docker build -t radar-frontend:railway-check ./frontend
.\backend\.venv\Scripts\python.exe scripts\postgres_acceptance.py --container-tests --backend-image radar-backend:railway-check --frontend-image radar-frontend:railway-check --out .test-support/railway-acceptance-linux
```

## Files in this change

- `backend/app/core/config.py`
- `backend/database/migrations/env.py`
- `backend/workers/migrate.py`
- `backend/workers/railway_collector.py`
- `backend/tests/test_railway_deployment.py`
- `backend/tests/test_postgres_acceptance.py`
- `frontend/Dockerfile`
- `frontend/nginx.conf`
- `frontend/docker-entrypoint.d/40-radar-upstream.sh`
- `scripts/postgres_acceptance.py`
- `RAILWAY_DEPLOYMENT.md`
- `RAILWAY_DEPLOYMENT_REPORT.md`

The existing stash, untracked scraper, accidental terminal-output file,
`backend/.env`, local PostgreSQL volumes and 1,362 institutions were preserved.
Generated caches, evidence, private values and unrelated files are excluded.

## Owner/provider handoff

Authorize Railway account/project access and its GitHub repository integration.
Use the service/variable table in `RAILWAY_DEPLOYMENT.md` to provision isolated
staging first. Supply provider secrets through Railway, never through Git.
After staging's actual generated URL passes acceptance, identify the owned
Cloudflare hostname/zone and authorize only its required records. Inspect origin
certificates before any SSL/proxy changes; no zone security downgrade is authorized.
Production requires owner approval, merged main, required CI and verified backups.
Live Brabble collection remains off until key and permission requirements are met.
No production records are automatically copied into a new database.

The commit SHA, PR URL and single observed CI result are recorded in the final
handoff message so this report does not contain a self-referential commit hash.

# DEVOPS-008 safe application rollback

Application rollback changes deployment images. Database restoration, schema
downgrade and data reconciliation are separate incident-owner approval paths.
This extends [rollback.md](rollback.md); keep DEVOPS-008 on develop.

## Decide and approve

Confirm the incident, approved cluster/namespace, failing component and previous
known-good release. Check pod/rollout status, public API failures, actual catalog
queries and authentication. Current /health probes establish liveness, not DB
readiness. Request-rate/latency thresholds are decision criteria only: exporters
and automatic rollback triggers are not provisioned by this repository.

Namespaces are hackathon-dev/test/staging/prod; Deployment/container names are
backend and frontend. Images are
ghcr.io/hackathonradarfinder/hackathonrdarfinder/{backend,frontend}:<40-character-SHA>.
Verify the target was successfully published/CI-tested on the approved protected
branch (develop for staging, main for prod), previously known-good, still available
and compatible with the current other component, configuration and schema.
Tags are not cryptographic attestations; restrict registry writes.

## Schema compatibility gate

Review release migrations and the current schema revision using approved read-only
tooling. Test the old backend with the current schema on disposable PostgreSQL 16.
Never run alembic downgrade -1 as an incident shortcut. The c8d9e0f1a2b3 downgrade
drops email_deliveries, destroying deduplication history; b7c8d9e0f1a2 drops
revoked_tokens, destroying revocation history; initial downgrade drops the schema.

Deployment workflows migrate before application rollout. If migration fails,
investigate the DB and retain the failed Job; application rollback cannot undo
partial migrations or repair corruption. Leave additive schema in place only when
the old application supports it. If compatibility is unknown, contain the incident
and prepare a reviewed forward fix. Downgrade/data recovery requires separate
approval, a tested plan, trusted restore-tested backup and data-loss analysis.

## Approved Kubernetes rollback

The helper accepts one component and explicit full SHA. It refuses all: approve
component order separately. A failed second component leaves a mixed release
requiring investigation. After approval, from the fix checkout:

```bash
export KUBE_CONTEXT=<approved-context>
export VERIFY_BASE_URL=https://<approved-deployed-host>
ROLLBACK_SHA=<known-good-full-40-character-SHA>
export ROLLBACK_CONFIRM="$KUBE_CONTEXT/hackathon-staging/backend/$ROLLBACK_SHA"
export SCHEMA_COMPATIBILITY_CONFIRMED="$ROLLBACK_SHA"
bash scripts/rollback-deployment.sh staging backend "$ROLLBACK_SHA"
```

Frontend uses frontend in the confirmation and component argument. Use prod and
hackathon-prod only after explicit production approval. The schema flag records
an operator decision, not an automatic proof. Verify HTTPS origin routing matches
the selected cluster/namespace. The script requires explicit context on every
kubectl command, validates inputs before mutation, selects the known-good image,
waits for rollout with a 300-second limit, checks the Deployment image, and runs
deployed HTTP checks. Every failure exits nonzero; there is no simulation/fallback.

Release approval/provenance are operator gates; this helper does not replace the
protected workflows or independently certify CI history. It changes only an image,
not Secrets/ConfigMaps or the whole workload specification. Incompatible configuration
requires its own reviewed versioned rollback. Never print Secret values/full env dumps.

## Verify running service

```bash
export VERIFY_BASE_URL=https://<approved-deployed-host>
bash scripts/verify-post-rollback.sh
```

Checks require HTTP 200, verified TLS, no redirects and bounded request time/size.
They verify Nginx /health, proxied /api/health, database-backed paginated /api/events/
and the frontend HTML shell. The deployment helper additionally waits for rollout
and checks the selected image. There is no /version endpoint reporting Git SHA;
local HEAD/build cannot identify deployed code. An empty catalog is allowed and
does not prove data integrity.

Finish browser/authenticated acceptance separately: login/register, search/details,
saved ownership/preferences, applicable predictions, admin denial and logout.
HTML-shell checks do not execute React. Monitor restored traffic and errors;
HTTP checks do not prove mailbox delivery or scraper correctness.

## Compose and workers

Compose builds local source and does not read BACKEND_IMAGE_TAG. Editing that
variable then running compose up does not select a previous release. Prepare a
reviewed image override for known-good frontend/backend tags and compatible config,
then recreate only application services on an approved target. Never use down -v,
delete the db service/volume, downgrade or restore as part of application rollback.
Compose retains PostgreSQL 16 on its named volume.

No Redis broker or worker Deployment is included in current overlays. Collection
and email workers are explicit jobs. Pause only the actual approved scheduler;
do not invent Deployment names, flush queues or reset sending/unknown email claims.
Preserve email history to prevent duplicate sends.

## Separate disaster recovery

Follow [database recovery](database-recovery.md) and [backup/restore](backup-and-restore.md)
for real data incidents. Restore a trusted archive into a new isolated DB, verify
catalog, authentication/revocations, saved records, email history and Alembic revision,
then obtain separate approval for reconciliation or connection switching. Never
promote partial table restores without relationship/integrity checks.

PR #72 is unsafe until its false-success and ephemeral-storage defects are fixed
and a disposable PostgreSQL restore exercise passes. There is no provisioned PITR,
15-minute RPO or measured 30-minute RTO/5-minute rollback guarantee. Treat these as
objectives to agree and measure. Use the incident template with redacted evidence.

# PR #71 review: NEEDS FIXES

Reviewed October 13, 2026. Original head:
`cecae1a1f8e272bc8bbad4229eb8a73d88589a92`, branch
`feature/DEVOPS-008-rollback-recovery`; GitHub API confirms it is open and targets
main. Review/fixes use a new `.review-pr71` worktree on
`fix/DEVOPS-008-rollback-safety`, based on current develop
`5c5c3f57cf94174000054ac1e37ef28641f9337b`.

All five changed files were reviewed: both shell scripts, the recovery document,
incident issue template and .gitignore change. The incident template is useful;
its YAML frontmatter parses. Adding .reports to .gitignore is noncritical and is
not required for the safe implementation. Original refs and all prior worktrees
are preserved. No deployment, restore, downgrade, push or merge was executed.

## Release-blocking findings

1. **Rollback errors are treated as success.** Original
   `scripts/rollback-deployment.sh:30` and `:35` suppress kubectl failures and
   simulate success. Missing kubectl also simulates Docker rollback without doing
   one. Invalid environments/components are accepted. No explicit approved context,
   target version, schema gate or rollout-status wait exists. This can target the
   wrong cluster and leaves outages undetected. Require explicit context/namespace,
   known-good image, approval and nonzero failure propagation; never simulate success.

2. **Verifier does not verify the running application.** Original
   `scripts/verify-post-rollback.sh:29` ignores failed builds; line 39 claims all
   checks succeeded. Local Git HEAD/package/docs/build cannot establish deployed
   image identity, readiness, DB connectivity or authentication. The package is
   frontend/package.json, not root/package.json. The rollback helper finds its
   verifier relative to the caller's working directory and can silently skip it.
   Resolve paths relative to the script, verify rollout/image and deployed HTTP
   catalog responses, and retain browser/authenticated checks as explicit gates.

3. **Migration guidance can delete production data/security state.** Document
   lines 100/102 suggest alembic downgrade -1 or a target downgrade without a
   specific reviewed compatibility/data-loss plan. Current c8d9e0f1a2b3 downgrade
   drops email_deliveries, erasing duplicate-send prevention history;
   b7c8d9e0f1a2 drops revoked_tokens, erasing logout revocations; the initial
   downgrade drops core tables. Application rollback does not imply DB rollback.
   Require old-app/current-schema testing; leave compatible expanded schema intact,
   otherwise contain and forward-fix. Separate data recovery approval from app rollback.

4. **Commands do not match infrastructure.** The proposed deployment names
   hackathon-radar-backend/frontend and namespaces production/staging differ from
   backend/frontend and hackathon-prod/staging. Published images use the repository
   prefix and full source SHA, not ghcr.io/hackathonradarfinder/backend:v1.0.0.
   Document line 82 edits BACKEND_IMAGE_TAG, which current Compose never reads:
   Compose builds local source and PostgreSQL 16 uses a persistent named volume.
   Line 139's --env=production is not the original script's positional interface.
   No worker Deployment, Redis broker/dead-letter queue, CDN or managed DB failover
   is provisioned by current overlays. No deployment configuration is actually
   modified by this PR, so those assumptions cannot be credited as working features.

5. **Disaster recovery is confused with application rollback and assumes unsafe backups.**
   PITR/restore does not undo only an application release: it can discard later
   writes, revocations and delivery history. The partial restore at document line
   149 references events instead of hackathons, calls a database a schema and omits
   relationship/auth/email/migration checks and a reviewed reconciliation implementation.
   There is no direct script call to PR #72, but daily-backup/PITR recovery has an
   operational dependency on backup functionality. PR #72 currently fabricates
   dumps after failure, reports failed restores as success and stores CronJob dumps
   in /tmp. Neither its original implementation nor a fictional latest backup can
   be used as recovery evidence. Restore only trusted archives into isolated new
   targets; approve reconciliation/connection switching separately.

6. **Health/trigger/recovery guarantees are unsupported.** Document line 159
   expects /version with a SHA, which is absent. /health is process liveness only.
   No deployed request metrics/automatic rollback rule implements the stated 5xx,
   latency or worker triggers. Queue reset/worker verification in the original
   script is an echo, not a check. RPO <=15 minutes, RTO <=30 minutes and rollback
   <=5 minutes are unmeasured objectives; current daily-backup/PITR provisioning
   does not establish them. Inspect configuration references/status without
   printing Secret values or full environment dumps.

## Minimal safe changes prepared

- Replacement `scripts/rollback-deployment.sh`: explicit environment/component,
  full known-good image SHA, context and exact confirmation. Backend additionally
  requires an operator schema-compatibility confirmation matching the SHA.
  Rejects all/invalid targets, missing kubectl and bad origin before mutation.
  Changes only the selected image, waits for rollout, checks desired image and
  executes deployed HTTP smoke checks. Every failure exits nonzero.
- `scripts/verify-post-rollback.sh` resolves its own location and delegates to
  `verify_post_rollback.py`: verified HTTPS, no credentials/query/fragment/redirects,
  bounded requests/responses, Nginx health, backend health, database-backed event
  pagination and frontend HTML shell. No local build or Git success substitutes.
- Updated existing rollback runbook; replaced proposed recovery guide with accurate
  architecture, migration risks, separate DR path and operator acceptance steps.
- Preserved the incident template with a redacted-evidence reminder.
- Added 29 safety/HTTP tests. No production configuration, migration, database
  restore, queue reset or volume cleanup was added.

These are code-level safeguards, not proof of a successful live rollback. Release
approval/provenance and schema compatibility remain operator gates. The helper
does not independently certify protected CI runs, revert ConfigMaps/Secrets,
restore full prior workload specifications or execute React/authenticated flows.
Mixed releases/config changes require a reviewed incident plan. Full SHA tags
are not registry-enforced immutable digests. See the runbook before use.

## Tests and runtime limits

- Four original defect probes reproduced using mocked kubectl/npm/git and a
  temporary checkout: suppressed kubectl/build failure, false verifier success,
  invalid target accepted and verification silently skipped from another cwd.
  These observations confirm defects; they are not passing feature tests.
- Original two shell scripts pass Bash syntax; original incident YAML parses.
- Fixed scripts pass two Bash syntax checks.
- Full operations suite: **60 passed, 0 failed, 0 skipped** (29 new rollback/HTTP
  tests plus 31 existing safeguards). Database commands, cluster calls and HTTP
  responses in new tests are mocked; no production mutation or network smoke occurred.
- Existing validate_ops.py passed workflow checks, YAML and all four rendered
  Kustomize overlays. Rendering does not connect to a cluster.
- Docker engine unavailable; no disposable Kubernetes/PostgreSQL runtime rehearsal
  was performed. ShellCheck is unavailable. Browser/authenticated acceptance and
  measured recovery timings remain unverified.
- Original reproducible probes retained in ignored .test-support/pr71_review_probes.py.

## Duplication, target branch and deadline

Develop already provides rollback.md, database-recovery.md, backup-and-restore.md,
manual protected deploy workflows, migration-before-rollout gating and operations
tests. Extend these; do not introduce competing deployment or recovery guarantees.
Retarget PR #71 to develop and reconcile with the prepared minimal patch. Main is
for reviewed release promotion, not primary integration. PR #72's review/fixes
remain separate and no assumption is made that they have been merged.

Before October 18: truthful failure handling, correct namespaces/image selection,
explicit context/approval/schema gate, no automatic downgrade/restore, deployed
health/catalog verification and a disposable rollback rehearsal with the target
backend/current schema. The safe application rollback subset is the release priority.

After MVP: managed PITR/failover, multi-region DR, CDN operations, automatic
telemetry-driven rollback, richer browser/auth automation, digest attestation and
measured RTO/RPO exercises. A 15-minute RPO becomes a release blocker only if the
team adopts it as a hard requirement. Basic trusted/durable backup availability
still matters for data incidents and must not be replaced by PR #72's false success.

Recommendation: **NEEDS FIXES**. Review and consolidate the safe application
rollback subset on develop, start disposable Docker/CI rehearsal when available,
and complete browser/auth acceptance. Keep advanced DR promises out of MVP
acceptance until provisioned and tested. No automatic merge is appropriate.

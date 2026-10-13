# PR #72 review: NEEDS FIXES

Reviewed October 13, 2026. PR is open, targets `main`, and its head is
`9508dd83980e0d67aece85265680b8c3a24af809` on
`feature/DEVOPS-007-database-backup-recovery`. GitHub API metadata was read using
the configured Git credential privately in memory; no credential was printed.
Current fetched develop is `5c5c3f57cf94174000054ac1e37ef28641f9337b`.

## Release blockers

1. **Fabricated backups and deletion after failure.**
   `scripts/backup-database.sh:50` writes synthetic SQL when pg_dump is missing or
   fails, then checksums it and exits zero. This is not a PostgreSQL custom archive
   or a backup of application data. At line 73 it prunes prior backups even after
   dump failure. Remove the fallback entirely; fail nonzero, validate real archives,
   publish atomically with unique names, and preserve old backups on failure.

2. **Destructive restore with false success.**
   `scripts/restore-database.sh:56` accepts an arbitrary target, uses --clean
   without approval/target safeguards, suppresses errors, and exits zero when
   pg_restore fails or is absent. Its schema verification is only an echo.
   Require an explicit new *_restore_* target and exact confirmation, refuse
   existing databases, restore with --exit-on-error --single-transaction
   --no-owner --no-privileges, and execute real schema/migration/data checks.
   Never use --clean on an application database.

3. **The scheduled backup is not recoverable.**
   `infrastructure/kubernetes/cronjobs/database-backup-cronjob.yaml` writes its
   only archive/checksum under /tmp with no PVC or remote upload. Pod/container
   replacement removes the files; keeping successful Job objects does not retain
   backups. Add approved durable protected storage and verified off-host transfer
   before calling the job operational. Retention must apply to verified stored
   copies, not ephemeral container files.

4. **Incompatible PostgreSQL/deployment configuration.**
   The CronJob uses postgres:15-alpine; Compose runs postgres:16-alpine. A
   PostgreSQL 15 pg_dump cannot dump a PostgreSQL 16 server. Use a reviewed client
   image compatible with PostgreSQL 16 and test its archive with restore tooling.
   The job namespace `production` differs from `hackathon-prod` and other
   environment namespaces. `database-credentials` host/username/password is not
   an existing Secret contract; current deployment uses `hackathon-db-secret`
   DATABASE_URL. That SQLAlchemy URL must not simply be passed to libpq.
   Provision an explicit secure libpq credential contract without printing secrets.
   DB name is configurable in Compose, not necessarily `hackathonradar`.
   Host-side Compose connects on 127.0.0.1:5433, not the script default 5432.
   Kubernetes PostgreSQL is externally provisioned. The CronJob is not referenced
   by existing Kustomize overlays, so normal deployment never installs it.
   The Secret reference avoids a hardcoded password, but backup file permissions
   and encrypted storage/transport are not enforced. Use private file permissions,
   least-privilege backup credentials and verified TLS (PGSSLMODE=verify-full with
   the appropriate CA) for remote PostgreSQL. Set spec.timeZone to Etc/UTC if
   02:00 UTC is intended, plus startingDeadlineSeconds, activeDeadlineSeconds and
   bounded backoffLimit so a hung job cannot block future Forbid runs indefinitely.

5. **Checksum validation does not authenticate the selected archive.**
   Restore line 42 invokes sha256sum --check on a sidecar, which verifies the
   path named inside it, not necessarily BACKUP_FILE. A valid checksum for a
   different file was accepted while the selected archive was invalid.
   Missing sidecars are silently skipped. If checksums are retained, validate the
   format and compare the recorded digest with the selected file's calculated
   digest before any DB operation. Also validate the custom archive. A checksum
   alone proves neither trusted origin nor successful recovery.

6. **Documentation promises functionality that is not provisioned.**
   The strategy claims zero data loss, <=15-minute RPO, <=30-minute RTO,
   AES-256/Object Lock, multi-tier cloud retention, continuous WAL, Slack alerts
   and automatic escalation without implementation/configuration/evidence.
   A daily logical dump has roughly a one-day worst-case RPO, potentially longer
   when backups fail. RDS PITR instructions do not configure PITR for Compose.
   Verification queries reference `events`, whereas the actual table is
   `hackathons`; `admin_reviews` is absent and model weights are filesystem
   artifacts. Document current schema, sensitive dump contents (including password
   hashes), actual guarantees and unverified objectives. Fix these claims before
   using the runbook during an incident.

## Duplication and branch target

Develop already contains `infrastructure/backup/backup_pg.sh`, `restore_pg.sh`
and `restore_test.sh`, with nonzero failure handling, private temporary files,
structural archive validation, no overwrite, explicit isolated restore targets,
confirmation, transactional restore and no automatic retention deletion.
It also contains `backup-and-restore.md`, `database-recovery.md` and 11 safety tests.
Those docs explicitly reserve DEVOPS-007 for coordinated scheduling/retention.

Retarget #72 to develop and rebase/resolve against the current implementation.
Keep one canonical engine. Either drop the duplicate scripts or retain thin aliases;
do not merge the original competing implementations. Main should receive the
reviewed release through the normal promotion path.

## Safe fixes prepared locally

Branch `fix/DEVOPS-007-backup-safety` in `.review-pr72` starts at current develop.
It is separate from all pre-existing worktrees and the original fetched PR ref.

- Added DEVOPS-007 entry-point aliases delegating to the existing canonical scripts.
- Supported explicit legacy DB_* variables without credential/default database
  fallbacks; restored targets require explicit arguments and confirmation.
- Replaced the proposed recovery strategy with accurate integration guidance,
  deployment requirements and limits.
- Added six tests for compatibility, failed-dump preservation, target/confirmation
  refusal, existing-target refusal and transactional failure propagation.

This is a **partial remediation / replacement patch**, not certification of the
original PR. The unsafe original CronJob is deliberately not brought into this
branch. A durable destination, Secret contract and approved scheduler integration
must be selected before implementing/enabling a replacement job. No remote PR
metadata was changed; no push, merge, restore or live database operation occurred.

## Verification

- Original PR: two Bash syntax checks passed; YAML parsed successfully.
- Original failure probes: all seven defect observations reproduced using
  shell-function mocks and temporary synthetic files only: fake dump success,
  pruning after failed dump, failed restore success, unconfirmed --clean without
  checksum, checksum for another file accepted, ephemeral CronJob storage, and
  PostgreSQL 15 client selection. These are confirmed defects, not passing feature tests.
- Existing canonical backup safeguards: 11 passed, 0 failed, 0 skipped.
- Safety aliases plus canonical safeguards: 17 passed, 0 failed, 0 skipped.
- Full operations regression suite with the aliases: 37 passed, 0 failed, 0 skipped.
- Fixed alias Bash syntax checks passed. ShellCheck is unavailable.
- Docker engine is unavailable; no disposable PostgreSQL backup/restore runtime
  test was performed. Real data recovery, archive portability, provider storage
  and measured RTO/RPO remain unverified.

Original review probes are retained under `.reports/pr72_review_checks.py` and
read the fetched original PR ref, so they can be repeated without modifying fixes.

## Before October 18 versus later

Before release: truthful nonzero failure handling, existing-target protection,
PostgreSQL 16 client compatibility, durable backups, correct credential/environment
wiring, a tested restore into a disposable PostgreSQL target, schema/application
checks, and failure visibility. Use existing canonical tooling while coordinating
the minimum durable daily backup job; do not enable the submitted CronJob as-is.

After MVP: multi-region weekly/monthly archives, Object Lock, automated retention
after verified copies, integrated alert escalation, and WAL/PITR may follow if the
team accepts a daily-backup RPO for MVP. If a 15-minute RPO is a hard release
requirement, PITR and its measured restore exercise are blockers, not enhancements.

Next owner actions: review the local patch, retarget/consolidate on develop,
choose durable storage and the credential contract, start isolated Docker/CI
PostgreSQL tests, and approve any later push/merge or operational rollout separately.

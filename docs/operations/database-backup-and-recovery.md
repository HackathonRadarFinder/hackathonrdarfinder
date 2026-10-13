# DEVOPS-007 backup and recovery integration

Use the existing [backup and restore runbook](backup-and-restore.md) and
[database recovery runbook](database-recovery.md). The DEVOPS-007 script names
are compatibility entry points to `infrastructure/backup/backup_pg.sh` and
`restore_pg.sh`, not a second backup implementation.

Both commands require explicit PGHOST/PGUSER (or legacy DB_HOST/DB_USER).
Backup additionally requires PGDATABASE (or DB_NAME) and protected BACKUP_DIR.
PGPORT/DB_PORT defaults to 5432. Use `PGPASSFILE`/`.pgpass` or securely injected
PGPASSWORD; do not put passwords in command arguments or enable shell tracing.
The Compose host connection is 127.0.0.1:5433, whereas its internal db service
uses port 5432. Kubernetes uses an externally provisioned PostgreSQL instance,
not a PostgreSQL Service included in these overlays.

Use PostgreSQL 16-compatible client tooling for the current Compose PostgreSQL
16 server. The FastAPI backend image is not a PostgreSQL client image.

```bash
# Against an approved source only, with credentials supplied securely:
export PGHOST=<approved-host> PGPORT=<correct-port> PGUSER=<backup-role>
export PGDATABASE=<actual-database> BACKUP_DIR=<protected-durable-directory>
bash scripts/backup-database.sh

# Restore only a trusted archive into a new, isolated target:
export PGHOST=<isolated-host> PGUSER=<restore-role>
export RESTORE_CONFIRM=radar_restore_manual
bash scripts/restore-database.sh /protected/archive.dump radar_restore_manual
```

Dump/client/database failures exit nonzero. Backup publication follows custom
archive validation and refuses overwrite; failure removes only its temporary
file. No automatic retention deletion occurs. Restore refuses existing targets,
requires exact confirmation, and uses exit-on-error plus a single transaction
without --clean. Failed newly created targets remain for investigation.
These aliases do not promise SHA-256 verification: canonical archive validation
is `pg_restore --list`, followed by actual isolated restore testing. If a checksum
sidecar is later introduced, verify the hash of the selected archive itself;
do not trust a filename embedded in an untrusted checksum file. A checksum is
not proof of trusted origin or successful recovery.

Current data includes `hackathons`, organizations, users/password hashes, roles,
saved_items, preferences, predictions, audit_logs, revoked_tokens, email_deliveries
and the Alembic revision. Treat dumps as sensitive. Model artifacts under ai/models
are filesystem assets and need their own versioned storage/recovery procedure.

Scheduling, encrypted off-host storage, retention, PITR and alerts remain to be
configured and measured. A daily logical dump can lose up to approximately one
day of changes; it does not meet a 15-minute RPO. No zero-data-loss, AES-256,
Object Lock, alerting or 30-minute RTO guarantee is established by these scripts.
For Compose PostgreSQL, PITR requires configured physical base backups and WAL
archiving (or an explicitly adopted managed service), not an RDS command alone.

Do not enable PR #72's original CronJob: it discards backups in /tmp, uses a
PostgreSQL 15 client and refers to a namespace/Secret outside the current
deployment contract. A replacement job must use a reviewed PostgreSQL 16 client
image, the approved environment namespace, explicit libpq credentials without
printing them, and durable protected storage plus off-host transfer verification.
Bound job duration/retries, prevent overlapping writers, monitor failures and
restore-test copies before applying retention. Retarget the PR to develop.

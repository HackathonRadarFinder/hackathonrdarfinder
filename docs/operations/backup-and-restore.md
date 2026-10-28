# PostgreSQL backup and restore

Scripts use native libpq PGHOST, PGPORT, PGUSER and PGDATABASE settings, with
PGPASSFILE/.pgpass or injected PGPASSWORD. Do not pass SQLAlchemy DATABASE_URL to
pg_dump, and do not put passwords in command-line arguments or run shell tracing.
Use compatible PostgreSQL clients (PostgreSQL 16 or newer for the Compose DB).
Store untrusted archives away from restores: SQL dumps can execute code.

Set BACKUP_DIR to a protected directory on durable storage. backup_pg.sh uses
umask 077, a unique filename, a temporary archive, and pg_restore --list integrity
validation before publishing it. It refuses overwrite. Listing a dump verifies
archive structure, not that a restore will succeed. Encrypt storage and transfer
backups off-host. Scheduling, encryption, credentials and storage are not
provisioned by this PR.

restore_pg.sh accepts only a new *_restore_* database, requires RESTORE_CONFIRM
to exactly equal TARGET_DB, and stops if createdb fails. It never uses --clean
and never restores into an existing database. It restores transactionally with
no-owner/no-privileges; a failed new target remains for operator diagnosis.

With approval, use a trusted archive and isolated PostgreSQL instance:

```bash
export PGHOST=<isolated-host> PGUSER=<restore-role>
export TARGET_DB=radar_restore_manual
export RESTORE_CONFIRM=radar_restore_manual
bash infrastructure/backup/restore_pg.sh /protected/backup.dump
bash infrastructure/backup/restore_test.sh /protected/backup.dump
```

restore_test.sh creates a unique database, installs cleanup only after creation,
checks users, roles, revoked_tokens and alembic_version, and drops only the
newly created test database. All local safety tests mock database commands;
no real restore or backup has been verified in this integration review.

Retention is operator-managed: define approved daily/weekly/monthly retention,
keep at least one restore-tested off-site copy, and verify recovery objectives
before deleting old backups. These scripts never delete completed archives.
Use PR #72's DEVOPS-007 work to coordinate scheduling/retention rather than
creating competing CronJobs here.

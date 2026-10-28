#!/usr/bin/env bash
# Restore only into a confirmed, new *_restore_* target. Never cleans a live DB.
set -euo pipefail
umask 077
BACKUP_FILE="${1:?Usage: restore-database.sh <trusted-archive> <new-target-db>}"
export TARGET_DB="${2:?Specify a new *_restore_* database}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
export PGHOST="${PGHOST:-${DB_HOST:?Set PGHOST or DB_HOST}}"
export PGUSER="${PGUSER:-${DB_USER:?Set PGUSER or DB_USER}}"
export PGPORT="${PGPORT:-${DB_PORT:-5432}}"
# RESTORE_CONFIRM must be supplied explicitly; the canonical script checks it.
exec bash "$SCRIPT_DIR/../infrastructure/backup/restore_pg.sh" "$BACKUP_FILE"

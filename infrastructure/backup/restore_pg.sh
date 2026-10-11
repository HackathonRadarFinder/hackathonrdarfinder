#!/usr/bin/env bash
set -euo pipefail
umask 077
BACKUP_FILE="${1:?Usage: restore_pg.sh <backup-file>}"
: "${PGHOST:?Set PGHOST}" "${PGUSER:?Set PGUSER}" "${TARGET_DB:?Set a new restore database}"
export PGHOST PGUSER PGPORT="${PGPORT:-5432}"
[[ "$PGPORT" =~ ^[0-9]+$ ]] && (( PGPORT > 0 && PGPORT <= 65535 )) || { echo "Invalid PGPORT" >&2; exit 1; }
[[ "$TARGET_DB" =~ ^[a-zA-Z][a-zA-Z0-9_]*_restore_[a-zA-Z0-9_]+$ && ${#TARGET_DB} -le 63 ]] || { echo "Target must be a new *_restore_* database" >&2; exit 1; }
[[ "${RESTORE_CONFIRM:-}" == "$TARGET_DB" ]] || { echo "RESTORE_CONFIRM must exactly match TARGET_DB" >&2; exit 1; }
[[ -f "$BACKUP_FILE" && -r "$BACKUP_FILE" && -s "$BACKUP_FILE" ]] || { echo "Invalid archive" >&2; exit 1; }
BACKUP_FILE="$(cd -- "$(dirname -- "$BACKUP_FILE")" && pwd -P)/$(basename -- "$BACKUP_FILE")"
pg_restore --list "$BACKUP_FILE" >/dev/null
# Refuse existing targets: never suppress createdb failures or use --clean.
createdb -w -- "$TARGET_DB"
pg_restore -w --exit-on-error --single-transaction --no-owner --no-privileges -d "$TARGET_DB" "$BACKUP_FILE"
printf 'Restored new database: %s\n' "$TARGET_DB"
# On failure the new target is retained for diagnosis; do not promote it.

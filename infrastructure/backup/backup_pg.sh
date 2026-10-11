#!/usr/bin/env bash
set -euo pipefail
umask 077
: "${PGHOST:?Set PGHOST}" "${PGUSER:?Set PGUSER}" "${PGDATABASE:?Set PGDATABASE}"
export PGHOST PGUSER PGDATABASE
export PGPORT="${PGPORT:-5432}"
[[ "$PGPORT" =~ ^[0-9]+$ ]] && (( PGPORT > 0 && PGPORT <= 65535 )) || { echo "Invalid PGPORT" >&2; exit 1; }
[[ "$PGDATABASE" =~ ^[a-zA-Z][a-zA-Z0-9_]{0,62}$ ]] || { echo "Invalid PGDATABASE" >&2; exit 1; }
# Use PGPASSFILE/.pgpass or an externally injected PGPASSWORD; no password defaults.
BACKUP_DIR="${BACKUP_DIR:?Set a protected backup directory}"
mkdir -p -- "$BACKUP_DIR"
BACKUP_DIR="$(cd -- "$BACKUP_DIR" && pwd -P)"
BACKUP_FILE="$BACKUP_DIR/${PGDATABASE}_$(date -u +%Y%m%dT%H%M%S)_${BASHPID}.dump"
[[ ! -e "$BACKUP_FILE" ]] || { echo "Backup already exists" >&2; exit 1; }
PARTIAL="$(mktemp "$BACKUP_DIR/.backup.XXXXXXXX")"
trap 'rm -f -- "$PARTIAL"' EXIT
pg_dump -w -Fc -f "$PARTIAL"
[[ -s "$PARTIAL" ]] || { echo "Empty backup" >&2; exit 1; }
pg_restore --list "$PARTIAL" >/dev/null
# No overwrite, including a file created concurrently.
ln -- "$PARTIAL" "$BACKUP_FILE"
printf 'Verified archive: %s\n' "$BACKUP_FILE"
# Retention and encrypted off-site storage are operator-managed; never delete
# backups automatically before restore verification and retention approval.

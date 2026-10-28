#!/usr/bin/env bash
set -euo pipefail
umask 077
BACKUP_FILE="${1:?Usage: restore_test.sh <backup-file>}"
: "${PGHOST:?Set PGHOST}" "${PGUSER:?Set PGUSER}"
export PGHOST PGUSER PGPORT="${PGPORT:-5432}"
[[ "$PGPORT" =~ ^[0-9]+$ ]] && (( PGPORT > 0 && PGPORT <= 65535 )) || { echo "Invalid PGPORT" >&2; exit 1; }
[[ -f "$BACKUP_FILE" && -r "$BACKUP_FILE" && -s "$BACKUP_FILE" ]] || { echo "Invalid archive" >&2; exit 1; }
BACKUP_FILE="$(cd -- "$(dirname -- "$BACKUP_FILE")" && pwd -P)/$(basename -- "$BACKUP_FILE")"
pg_restore --list "$BACKUP_FILE" >/dev/null
TEST_DB="radar_restore_test_$(date -u +%Y%m%d%H%M%S)_${BASHPID}"
createdb -w -- "$TEST_DB"
# Install cleanup only after this process successfully created the target.
trap 'dropdb -w -- "$TEST_DB"' EXIT
pg_restore -w --exit-on-error --single-transaction --no-owner --no-privileges -d "$TEST_DB" "$BACKUP_FILE"
for table in users roles revoked_tokens alembic_version; do
  found="$(psql -w -X -v ON_ERROR_STOP=1 -d "$TEST_DB" -Atc "SELECT to_regclass('public.$table') IS NOT NULL")"
  [[ "$found" == t ]] || { echo "Required table missing: $table" >&2; exit 1; }
done
echo "Isolated restore and AUTH schema checks passed"

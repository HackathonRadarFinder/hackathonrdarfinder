#!/usr/bin/env bash
# DEVOPS-007 compatibility entry point; the reviewed implementation is canonical.
set -euo pipefail
umask 077
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
export PGHOST="${PGHOST:-${DB_HOST:?Set PGHOST or DB_HOST}}"
export PGUSER="${PGUSER:-${DB_USER:?Set PGUSER or DB_USER}}"
export PGDATABASE="${PGDATABASE:-${DB_NAME:?Set PGDATABASE or DB_NAME}}"
export PGPORT="${PGPORT:-${DB_PORT:-5432}}"
exec bash "$SCRIPT_DIR/../infrastructure/backup/backup_pg.sh"

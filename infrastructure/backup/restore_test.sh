#!/usr/bin/env bash
set -euo pipefail

BACKUP_FILE="${1:-}"
TEST_DB="hackathon_radar_restore_test"
PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5432}"
PGUSER="${PGUSER:-postgres}"

if [[ -z "${BACKUP_FILE}" ]]; then
  echo "Usage: $0 <backup-file>"
  exit 1
fi

if [[ ! -f "${BACKUP_FILE}" ]]; then
  echo "Backup file not found: ${BACKUP_FILE}"
  exit 1
fi

createdb -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" "${TEST_DB}" || true
PGPASSWORD="${PGPASSWORD:-postgres}" pg_restore \
  -h "${PGHOST}" \
  -p "${PGPORT}" \
  -U "${PGUSER}" \
  -d "${TEST_DB}" \
  --clean --if-exists "${BACKUP_FILE}"

psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d "${TEST_DB}" -c "SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name;"

dropdb -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" --if-exists "${TEST_DB}"

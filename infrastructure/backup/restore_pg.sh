#!/usr/bin/env bash
set -euo pipefail

BACKUP_FILE="${1:-}"
TARGET_DB="${TARGET_DB:-hackathon_radar_restore}"
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

createdb -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" "${TARGET_DB}" || true
PGPASSWORD="${PGPASSWORD:-postgres}" pg_restore \
  -h "${PGHOST}" \
  -p "${PGPORT}" \
  -U "${PGUSER}" \
  -d "${TARGET_DB}" \
  --clean --if-exists "${BACKUP_FILE}"

# Hackathon Radar: Database Backup & Recovery Strategy

## 1. Overview & Policy Objective
The **Hackathon Radar** database contains critical platform data, including verified hackathon opportunities, historical recurrence data, organization profiles, builder skill preferences, admin moderation reviews, and audit trails.

This strategy establishes automated backup routines, secure offsite storage, point-in-time recovery (PITR) procedures, and periodic restore testing to ensure zero data loss during infrastructure incidents or human errors.

### Service Level Objectives
- **Recovery Point Objective (RPO)**: $\le 15\text{ minutes}$ (maximum acceptable data loss).
- **Recovery Time Objective (RTO)**: $\le 30\text{ minutes}$ (maximum duration to restore full database functionality).

---

## 2. Backup Tiers, Schedules & Retention

| Backup Tier | Frequency | Tool / Mechanism | Storage Location | Retention Window |
| :--- | :--- | :--- | :--- | :--- |
| **Continuous WAL** | Continuous (every 5m) | PostgreSQL WAL-G / Cloud PITR | Encrypted Cloud Bucket (`s3://...-wal/`) | 7 Days (PITR window) |
| **Daily Snapshot** | Daily at 02:00 UTC | `pg_dump -Fc` / Volume Snapshot | Separate Encrypted Storage (`s3://...-daily/`) | 7 Days |
| **Weekly Retained**| Sundays at 03:00 UTC | Full database dump | Secondary Cloud Region | 4 Weeks |
| **Monthly Archive** | 1st of each month | Full database archive | Glacier / Coldline Deep Archive | 12 Months |

---

## 3. Data Scope & Security Considerations

### 3.1 Persistent Data Covered
- `events`: Active, historical, and forecasted hackathons.
- `organizations`: Verified sponsors, universities, and tech platforms.
- `users`: Developer profiles, skills, and notification settings.
- `predictions`: Model weights, confidence scores, and past recurrence records.
- `admin_reviews`: Moderation queues, approval history, and data quality flags.
- `audit_logs`: User and system operational logs.

### 3.2 Security & Compliance
- **Encryption in Transit & at Rest**: All backups are encrypted using **AES-256** server-side encryption.
- **Isolated Storage**: Backups are written to an isolated cloud bucket in a separate AWS/GCP account with strict IAM policies and **Object Lock (WORM - Write Once, Read Many)** to prevent ransomware tampering.
- **Secret Hygiene**: Database connection strings, JWT signing keys, and external API tokens are managed via Secret Manager and never written to relational tables or backup dumps.

---

## 4. Manual Backup Procedure

To generate an immediate manual backup (e.g. prior to applying a risky schema migration or deploying a major release):

```bash
# 1. Set environment variables
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_NAME="hackathonradar"
export DB_USER="radar_admin"
export BACKUP_DIR="./backups"

# 2. Run backup script
./scripts/backup-database.sh

# Or execute raw pg_dump with custom compressed format:
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
mkdir -p "${BACKUP_DIR}"
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
  --format=custom \
  --blobs \
  --verbose \
  --file="${BACKUP_DIR}/hackathonradar_${TIMESTAMP}.dump"

# 3. Generate SHA-256 checksum
sha256sum "${BACKUP_DIR}/hackathonradar_${TIMESTAMP}.dump" > "${BACKUP_DIR}/hackathonradar_${TIMESTAMP}.dump.sha256"
```

---

## 5. Database Restore Procedure

### 5.1 Restoring to an Isolated Staging Environment
Before applying backups to production, always test restoration in staging or a local container:

```bash
# 1. Create a clean isolated database
createdb -h "$DB_HOST" -U "$DB_USER" hackathonradar_restored

# 2. Run restore script
./scripts/restore-database.sh ./backups/hackathonradar_20261010_020000.dump hackathonradar_restored

# Or run pg_restore directly:
pg_restore -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
  -d hackathonradar_restored \
  --verbose \
  --clean \
  --if-exists \
  ./backups/hackathonradar_20261010_020000.dump
```

### 5.2 Post-Restore Integrity Verification
Run verification queries to confirm table counts and data integrity:
```sql
SELECT 'events' AS table_name, count(*) FROM events
UNION ALL
SELECT 'organizations', count(*) FROM organizations
UNION ALL
SELECT 'users', count(*) FROM users;
```

---

## 6. Point-in-Time Recovery (PITR) Procedure

In the event of accidental data modification or drop:
1. Determine the target recovery timestamp (e.g., `2026-10-10 14:22:00 UTC` — 2 minutes prior to corruption).
2. On cloud-managed PostgreSQL (AWS RDS / GCP Cloud SQL):
   ```bash
   aws rds restore-db-instance-to-point-in-time \
     --source-db-instance-identifier hackathon-radar-prod \
     --target-db-instance-identifier hackathon-radar-recovered \
     --restore-time "2026-10-10T14:22:00Z"
   ```
3. Verify restored tables on the new instance.
4. Update application database secret and restart backend services.

---

## 7. Failure Handling & Alerting
- If the automated backup job fails or exits with a non-zero exit code:
  - An alert is pushed to Prometheus / Alertmanager: `DatabaseBackupFailed`.
  - Notification sent to `#devops-alerts` in Slack.
  - On-call engineer investigates within 2 business hours.
- If two consecutive backup cycles fail, an escalated P1 incident is raised automatically.

# Backup and restore runbook

## Purpose
Establish a repeatable PostgreSQL backup and restore process.

## Backup strategy
- Use `pg_dump` for logical backups and `pg_restore` for restore operations.
- Store backups outside the application pod filesystem.
- Encrypt backups at rest if the environment requires it.
- Keep retention aligned with the team’s RPO/RTO target.

## Example commands
```bash
pg_dump -Fc -d "$DATABASE_URL" -f /backup/hackathon_radar_$(date +%F_%H%M%S).dump
pg_restore -d hackathon_radar_restore /backup/hackathon_radar.dump
```

## Restore test procedure
1. Obtain a test backup.
2. Create a temporary PostgreSQL database.
3. Restore the backup into the temporary database.
4. Validate connectivity and required tables.
5. Clean up the test database.

## Verification
- Required tables exist.
- Application can connect to the restored database.
- Key queries and migrations succeed.

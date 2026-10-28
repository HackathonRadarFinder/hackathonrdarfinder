# Database recovery

Stop and obtain incident-owner approval before changing any live database.
Restore a trusted backup into a new isolated target using backup-and-restore.md,
validate authentication including revoked tokens, migration revision and key
module data, and rehearse application connectivity. Promote the recovered DB
only through an approved connection-switch procedure. A successful archive
listing alone does not prove recovery. Never run --clean against an existing DB.

RTO/RPO targets must be agreed and measured by the team. This PR does not
establish a 15-minute RPO or a four-hour RTO: no backup schedule, off-site storage,
point-in-time recovery or measured recovery exercise is provisioned.

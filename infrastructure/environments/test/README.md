# TEST environment

## Purpose
Validate the same GHCR image in an isolated environment before staging and production approval.

## Defaults
- Namespace: `hackathon-test`
- Replicas: 2
- Hardware profile: moderately sized but still disposable
- Database: temporary/test database instance

## Verification
- Automated validation completes.
- Health checks pass.
- Service connectivity and migration status are confirmed.

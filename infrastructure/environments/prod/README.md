# PROD environment

## Purpose
Production deployment is approval-gated and requires a known-good immutable image.

## Defaults
- Namespace: `hackathon-prod`
- Replicas: 3
- HPA min/max tuned for production load
- Database: production database with backup automation and monitoring

## Verification
- Manual approval required.
- Rollout status and health checks pass.
- Application and database remain stable after deployment.

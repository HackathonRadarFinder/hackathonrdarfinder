# STAGING environment

## Purpose
Production-like environment used for final confidence checks before approval-based deployment to production.

## Defaults
- Namespace: `hackathon-staging`
- Replicas: 2
- Production-like resources, health checks, and ingress configuration
- Database: staging database with realistic configuration

## Verification
- Same GHCR image as TEST, no rebuild.
- Smoke tests and readiness checks pass.
- Dashboards and alerts are healthy.

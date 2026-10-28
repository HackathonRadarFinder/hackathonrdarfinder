# Troubleshooting guide

## Purpose
Use this guide to investigate common runtime problems.

## Common issues
### Backend fails to start
- Check environment variables such as `DATABASE_URL` and `SECRET_KEY`.
- Confirm PostgreSQL is reachable.
- Review the container logs.

### Database connection issues
- Confirm the database host and port.
- Validate credentials in the secret or environment.
- Run `pg_isready` against the target database.

### Frontend blank page
- Check the frontend service and ingress routing.
- Confirm the built assets are present in the container.
- Verify API URL configuration.

## Commands
```bash
kubectl logs deployment/backend -n hackathon-dev
kubectl describe deployment/backend -n hackathon-dev
kubectl get endpoints -n hackathon-dev
```

## Escalation
Escalate to the platform owner if issues persist across multiple replicas or environments.

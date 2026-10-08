# Monitoring runbook

## Purpose
Document the metrics, dashboards, and log access patterns for the application and Kubernetes cluster.

## Suggested stack
- Prometheus for metrics collection.
- Grafana for dashboards.
- Loki or a compatible log backend for application logs.

## Metrics to monitor
- Backend request rate, latency, 4xx, and 5xx.
- Kubernetes CPU, memory, pod restarts, and availability.
- Database availability, connection count, storage, and backup status.

## Commands
```bash
kubectl -n hackathon-prod top pods
kubectl -n hackathon-prod get events --sort-by=.metadata.creationTimestamp
kubectl logs -l app=backend -n hackathon-prod --tail=100
```

## Verification
- Dashboards show healthy runtime metrics.
- Alerting rules fire only under the expected conditions.
- Logs are searchable by namespace, pod, and level.

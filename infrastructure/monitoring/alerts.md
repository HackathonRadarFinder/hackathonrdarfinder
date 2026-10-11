# Alerts and coverage

The example Prometheus ConfigMap includes RadarEndpointUnavailable and
RadarProbeExporterUnavailable executable rules. Both require an externally
managed Prometheus and blackbox exporter. They have not been exercised live.

Investigate failed probes through deployment events, pod status and approved
logs; distinguish an unreachable exporter from an unhealthy HTTP target.
Database readiness, application 5xx rate, restarts, CPU/memory pressure and
backup freshness remain proposed alert coverage. They require exporters,
kube-state-metrics/metrics collection and tested Alertmanager routing. See
PR #70 and docs/operations/monitoring.md; do not describe proposals as active alerts.

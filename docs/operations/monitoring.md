# Monitoring status and setup

The application does not expose /metrics, and Nginx does not have a metrics
exporter. infrastructure/monitoring/prometheus.yaml therefore provides an
example ConfigMap for externally managed Prometheus and a blackbox exporter.
It probes HTTP /health through Services in hackathon-dev; change target namespaces
for other environments. Mount prometheus.yml and alerts.yml at /etc/prometheus.
Provision blackbox-exporter in observability with the http_2xx module and verify
DNS/network access before installing this example configuration.

Two executable rules cover failed HTTP probes and failed probe scrapes. These
are process reachability checks, not DB readiness or request-rate metrics.
Prometheus, blackbox exporter, Alertmanager, notification routing and dashboards
are not installed by this repository. The YAML was parsed locally; promtool and
live scrapes were unavailable. Do not claim request latency, 5xx rates, CPU,
memory, backup freshness or DB metrics are monitored until exporters and rules
are provisioned and exercised. Coordinate broader monitoring with PR #70.

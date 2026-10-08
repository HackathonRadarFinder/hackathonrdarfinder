# Infrastructure overview

This repository keeps deployment configuration cloud-neutral and Kubernetes-native.

## Components
- Dockerfiles for backend and frontend
- local Docker Compose for app + PostgreSQL
- GitHub Actions workflows for CI and immutable GHCR image publishing
- Kubernetes manifests for namespaces, deployments, services, ingress, and autoscaling
- backup and restore scripts for PostgreSQL
- operation runbooks under `docs/operations`

## Required manual configuration
- GitHub Environment protection for `production`
- Kubernetes cluster credentials and namespace setup
- Secret values and DB connection strings
- DNS and TLS for ingress hostnames
- Prometheus/Grafana/Loki integration for a full observability stack

## Deployment principle
The same GHCR image, tagged by Git SHA, should flow through DEV -> TEST -> STAGING -> PROD without rebuilding per environment.

# Environment management

Namespaces: hackathon-dev, hackathon-test, hackathon-staging, hackathon-prod.
ENVIRONMENT is supplied through hackathon-app-config; DEBUG is false. DATABASE_URL
and SECRET_KEY come only from namespace-specific Secrets. Avoid shared signing
keys/databases across environments. Unsupported APP_ENV and runtime VITE_API_BASE_URL
settings were removed: the Vite build cannot consume container-start environment
variables. Nginx provides the same-origin /api/ proxy.

All environments share the base resource requests/limits. Dev uses one initial
replica and HPA 1..2; test uses two initial replicas and HPA 1..4; staging uses
two initial replicas and HPA 2..6; prod uses three initial replicas and HPA 2..10
for both frontend and backend. HPA can change those initial counts. Actual
capacity limits need load testing. Hosts in checked-in overlays are placeholders;
the deployment workflow supplies INGRESS_HOST and TLS_SECRET per environment.

Configure environment-scoped credentials, reviewer protections, namespace
provisioning and databases as described in deployment.md before dispatching.

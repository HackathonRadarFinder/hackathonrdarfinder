# TEST environment

Namespace: hackathon-test. See docs/operations/environment-management.md for
replicas/HPA and deployment.md for prerequisites. CPU/memory limits are shared
with the base and need load validation. Separate databases, signing keys, GHCR
pull credentials, ingress/TLS and environment protection require operator setup.

Render with kubectl kustomize infrastructure/kubernetes/overlays/test.
Rendering is offline and does not validate a live deployment. Image and DNS
placeholders must be replaced through the approved manual deployment workflow.

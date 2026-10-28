#!/usr/bin/env bash
# Approved Kubernetes application rollback only; never alters database or queues.
set -euo pipefail
ENVIRONMENT="${1:?Usage: rollback-deployment.sh <dev|test|staging|prod> <backend|frontend> <known-good-SHA>}"
COMPONENT="${2:?Specify backend or frontend}"
IMAGE_SHA="${3:?Specify the full known-good release SHA}"
case "$ENVIRONMENT" in dev|test|staging|prod) ;; *) echo "Invalid environment" >&2; exit 1;; esac
case "$COMPONENT" in backend|frontend) ;; *) echo "Invalid component; roll components separately" >&2; exit 1;; esac
[[ "$IMAGE_SHA" =~ ^[0-9a-f]{40}$ ]] || { echo "Invalid release SHA" >&2; exit 1; }
: "${KUBE_CONTEXT:?Specify the approved cluster context}" "${VERIFY_BASE_URL:?Specify the deployed HTTPS origin}"
NAMESPACE="hackathon-$ENVIRONMENT"
[[ "${ROLLBACK_CONFIRM:-}" == "$KUBE_CONTEXT/$NAMESPACE/$COMPONENT/$IMAGE_SHA" ]] || { echo "Explicit rollback confirmation is required" >&2; exit 1; }
if [[ "$COMPONENT" == backend && "${SCHEMA_COMPATIBILITY_CONFIRMED:-}" != "$IMAGE_SHA" ]]; then
  echo "Confirm this backend SHA supports the current schema before rollback" >&2; exit 1
fi
command -v kubectl >/dev/null || { echo "kubectl is required; no simulation" >&2; exit 1; }
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# Reject invalid origins before changing the deployment.
python "$SCRIPT_DIR/verify_post_rollback.py" --validate-only
IMAGE="ghcr.io/hackathonradarfinder/hackathonrdarfinder/$COMPONENT:$IMAGE_SHA"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" set image "deployment/$COMPONENT" "$COMPONENT=$IMAGE"
kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" rollout status "deployment/$COMPONENT" --timeout=300s
DEPLOYED_IMAGE="$(kubectl --context "$KUBE_CONTEXT" -n "$NAMESPACE" get "deployment/$COMPONENT" -o "jsonpath={.spec.template.spec.containers[?(@.name=='$COMPONENT')].image}")"
[[ "$DEPLOYED_IMAGE" == "$IMAGE" ]] || { echo "Deployed image differs from approved target" >&2; exit 1; }
bash "$SCRIPT_DIR/verify-post-rollback.sh"
echo "Application rollout and HTTP catalog checks passed; complete browser and authenticated acceptance checks."

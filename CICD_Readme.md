# CI/CD overview

PRs targeting develop/main run backend tests, frontend lint/build, offline
infrastructure validation, recovery safety tests, and Docker build/smoke tests.
Python 3.12 and Node 24 are used. Actions are pinned to verified commit SHAs.

Pushes to develop/main also invoke Build and Publish. That workflow calls the
same CI suite and publishes only after all jobs pass. Backend/frontend images
use the full commit SHA in GHCR. SHA tags provide source traceability but are
not cryptographically immutable registry digests; protect write access to GHCR.

Deployment workflows are manual. Run dev/test/staging workflows from develop,
and production from main. Supply the full lowercase commit SHA. The gate checks
branch ancestry and the latest successful push CI and publisher runs for that
commit. PR runs cannot authorize deployment. Each environment serializes
rollouts, verifies image availability and provisioned secrets, migrates before
applying workloads, then waits for both deployments.

Production required reviewers, protected branches, and prevention of approval
by the initiating actor must be configured by a repository administrator. These
settings cannot be enforced by workflow YAML and have not been verified here.

See docs/operations/deployment.md for prerequisites, environment variables,
namespace-scoped credentials, migration risks, and explicit approval boundaries.
No deployment has been validated against a live cluster. See the integration
review for executed checks and remaining blockers.

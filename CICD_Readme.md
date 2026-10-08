# CI/CD Pipeline Overview

This repository implements a cloud-neutral GitHub Actions + Docker + GHCR + Kubernetes release flow that promotes immutable images across environments instead of rebuilding for each stage.

## 1. Release flow

The intended promotion path is:

```text
feature branch
  -> pull request
  -> develop
  -> CI validation
  -> build backend + frontend images
  -> push immutable SHA tags to GHCR
  -> DEV
  -> TEST
  -> STAGING
  -> PROD approval gate
```

The key rule is that the same Git commit SHA produces the same Docker image and that image is promoted. It is not rebuilt for each environment.

---

## 2. CI workflow

The validation pipeline is defined in `.github/workflows/ci.yml`.

### Trigger conditions
- pull requests targeting `develop` or `main`
- pushes to `develop` or `main`

### Validation performed
- backend dependency installation
- PostgreSQL service startup
- Alembic migration execution
- backend `pytest` suite
- frontend `npm ci`
- frontend lint
- frontend production build
- Docker image builds for backend and frontend

This stage acts as the quality gate before the image is pushed to GHCR.

---

## 3. Immutable image build and publish

The repository includes `.github/workflows/build-and-publish.yml`.

### What it does
- checks out the repository
- sets a Git SHA-based image tag
- authenticates to GHCR using `GITHUB_TOKEN`
- builds the backend image
- builds the frontend image
- pushes both images to GHCR using the same immutable commit SHA

Example:

```text
ghcr.io/<owner>/<repo>/backend:<commit-sha>
ghcr.io/<owner>/<repo>/frontend:<commit-sha>
```

This is the build-once/publish-once model required by the task.

---

## 4. Deployment workflows

The environment deployment workflows are:

- `.github/workflows/deploy-dev.yml`
- `.github/workflows/deploy-test.yml`
- `.github/workflows/deploy-staging.yml`
- `.github/workflows/deploy-prod.yml`

These workflows do not rebuild the image. They accept an existing `image_tag` input and deploy the already-published artifact to the configured environment.

### Important behavior
- same target image is used across environments
- the image is selected by commit SHA
- image validation is performed before deployment
- the Kubernetes manifest is updated to the exact image tag before `kubectl apply`

---

## 5. Kubernetes and Kustomize

The repository contains Kustomize resources under `infrastructure/kubernetes/`.

### Structure
- `base/` holds shared manifests
- `overlays/dev` and the other environment overlays customize namespace and image selection

### Deployment model
- base resources define deployments, services, config maps, ingress, and HPA
- environment overlays set namespace, environment configuration, and immutable image reference
- deployment workflows inject the selected SHA tag into the kustomize image reference before rollout

This keeps the deployment pattern cloud-neutral while still aligning with real Kubernetes best practices.

---

## 6. GitHub environments and approvals

The deployment workflows use GitHub Environments for:

- development
- test
- staging
- production

Production is the approval-gated environment, which matches the required promotion model.

The repository admin must configure the required environment secrets/variables, especially:

- `KUBE_CONFIG_DATA`
- any environment-specific variables required by the cluster

No secrets should be committed to the repo.

---

## 7. Required manual setup outside the repo

The codebase is ready for deployment, but the following must be configured in the GitHub project or cluster by an admin:

- Kubernetes cluster access via `KUBE_CONFIG_DATA`
- namespace creation if needed
- ingress domain and TLS configuration
- external PostgreSQL endpoint if the project uses a managed database outside the cluster
- environment-specific secret values for database and app configuration

This is intentionally kept outside the codebase so sensitive values are not committed.

---

## 8. Local validation commands

### Backend
```bash
cd backend
python -m pip install -r requirements.txt
pytest -q
```

### Frontend
```bash
cd frontend
npm ci
npm run lint
npm run build
```

### Docker
```bash
docker build -t hackathon-radar-backend:test ./backend
docker build -t hackathon-radar-frontend:test ./frontend
docker compose config
```

### Kustomize validation
```bash
kubectl kustomize infrastructure/kubernetes/overlays/dev
kubectl kustomize infrastructure/kubernetes/overlays/test
kubectl kustomize infrastructure/kubernetes/overlays/staging
kubectl kustomize infrastructure/kubernetes/overlays/prod
```

---

## 9. Traceability requirement

The release model preserves a clear relationship between the Git SHA and the deployed Docker image.

This means:
- artifact provenance is visible
- the same image can be promoted across environments
- rollback can reference a prior known-good SHA
- production changes can be traced back to the exact source commit

This is the most important correction in the implementation and is now reflected in the workflows and kustomize design.

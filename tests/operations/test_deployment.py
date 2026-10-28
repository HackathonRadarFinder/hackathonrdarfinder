import copy
from pathlib import Path
import sys
import shutil
import subprocess

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from prepare_deployment import prepare
from verify_release import validate_tag, validated_runs


@pytest.mark.parametrize("value", ["latest", "abc", "a" * 41, "A" * 40, "$(id)", "a'; touch /tmp/x; '"])
def test_reject_untrusted_image_tag(value):
    with pytest.raises(ValueError):
        validate_tag(value)


def fixtures():
    env = {"IMAGE_TAG": "a" * 40, "NAMESPACE": "hackathon-test", "INGRESS_HOST": "radar.example.com",
           "TLS_SECRET": "radar-tls", "IMAGE_PREFIX": "ghcr.io/owner/repo",
           "GITHUB_RUN_ID": "1234", "GITHUB_RUN_ATTEMPT": "1"}
    docs = [{"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": "hackathon-test"}},
            {"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": "config", "namespace": "hackathon-test"}},
            {"apiVersion": "apps/v1", "kind": "Deployment", "metadata": {"name": "backend", "namespace": "hackathon-test"},
             "spec": {"template": {"metadata": {"labels": {"app": "backend"}}, "spec": {
                 "automountServiceAccountToken": False, "securityContext": {"runAsNonRoot": True},
                 "containers": [{"name": "backend", "image": "placeholder", "env": [{"name": "SECRET_KEY", "valueFrom": {"secretKeyRef": {"name": "app", "key": "SECRET_KEY"}}}],
                                 "ports": [8000], "livenessProbe": {}, "readinessProbe": {}, "startupProbe": {}}]}}}},
            {"apiVersion": "networking.k8s.io/v1", "kind": "Ingress", "metadata": {"name": "ingress", "namespace": "hackathon-test"},
             "spec": {"rules": [{"host": "placeholder"}]}}]
    return docs, env


def test_migration_uses_release_image_and_secret_references():
    docs, env = fixtures()
    name, config, job, workloads = prepare(copy.deepcopy(docs), env)
    assert name == "backend-migrate-aaaaaaaaaaaa-1234-1"
    pod = job["spec"]["template"]["spec"]
    container = pod["containers"][0]
    assert container["image"] == "ghcr.io/owner/repo/backend:" + "a" * 40
    assert container["command"] == ["python", "-m", "alembic", "upgrade", "head"]
    assert container["env"] == docs[2]["spec"]["template"]["spec"]["containers"][0]["env"]
    assert not set(container).intersection({"livenessProbe", "readinessProbe", "startupProbe", "ports"})
    assert job["spec"]["template"]["metadata"]["labels"] == {"app": "backend-migration"}
    assert job["spec"]["backoffLimit"] == 0
    assert not any(doc["kind"] == "Namespace" for doc in config + workloads)
    assert workloads[-1]["spec"]["tls"] == [{"hosts": ["radar.example.com"], "secretName": "radar-tls"}]


@pytest.mark.parametrize("key,value", [
    ("NAMESPACE", "production"), ("INGRESS_HOST", "prod.example.invalid"),
    ("INGRESS_HOST", "$(id)"), ("TLS_SECRET", ""), ("IMAGE_PREFIX", "attacker/image"),
    ("INGRESS_HOST", "bad..example.com"), ("INGRESS_HOST", "-bad.example.com"),
    ("GITHUB_RUN_ID", "../unsafe"),
])
def test_reject_invalid_deployment_configuration(key, value):
    docs, env = fixtures()
    env[key] = value
    with pytest.raises(ValueError):
        prepare(docs, env)


def test_release_requires_ci_publish_and_latest_successful_attempt():
    runs = [{"path": path, "head_sha": "a" * 40, "head_branch": "main", "event": "push",
             "conclusion": "success", "run_number": 1, "run_attempt": 1}
            for path in [".github/workflows/ci.yml", ".github/workflows/build-and-publish.yml"]]
    assert validated_runs(runs, "a" * 40, "main")
    assert not validated_runs(runs[:1], "a" * 40, "main")
    assert not validated_runs(runs, "a" * 40, "develop")
    assert not validated_runs(runs, "b" * 40, "main")
    rerun = dict(runs[0], run_attempt=2, conclusion="failure")
    assert not validated_runs(runs + [rerun], "a" * 40, "main")
    assert not validated_runs([dict(run, event="pull_request") for run in runs], "a" * 40, "main")


@pytest.mark.skipif(not shutil.which("kubectl"), reason="kubectl unavailable")
@pytest.mark.parametrize("environment", ["dev", "test", "staging", "prod"])
def test_real_overlay_prepares_migration_and_matching_workloads(environment):
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(["kubectl", "kustomize", str(root / "infrastructure/kubernetes/overlays" / environment)],
                            check=True, capture_output=True, text=True)
    docs = list(yaml.safe_load_all(result.stdout))
    _, env = fixtures()
    env["NAMESPACE"] = f"hackathon-{environment}"
    _, _, migration, workloads = prepare(docs, env)
    backend = next(doc for doc in workloads if doc["kind"] == "Deployment" and doc["metadata"]["name"] == "backend")
    deployed = backend["spec"]["template"]["spec"]["containers"][0]
    migrated = migration["spec"]["template"]["spec"]["containers"][0]
    assert deployed["image"] == migrated["image"]
    assert deployed["env"] == migrated["env"]
    assert migration["metadata"]["namespace"] == env["NAMESPACE"]
    assert migration["spec"]["template"]["spec"]["securityContext"]["runAsNonRoot"]

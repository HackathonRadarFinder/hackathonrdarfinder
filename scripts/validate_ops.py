"""Offline workflow and Kustomize contract checks; never contacts a cluster."""
from pathlib import Path
import re
import subprocess

import yaml

ROOT = Path(__file__).resolve().parents[1]


def validate_workflows():
    for path in sorted((ROOT / ".github/workflows").glob("*.yml")):
        workflow = yaml.load(path.read_text(), Loader=yaml.BaseLoader)
        assert "on" in workflow and "jobs" in workflow, path
        assert workflow["permissions"]["contents"] == "read", path
        for job in workflow["jobs"].values():
            for step in job.get("steps", []):
                action = step.get("uses", "")
                assert not action or action.startswith("./") or re.fullmatch(r"[\w/-]+@[0-9a-f]{40}", action), (path, action)
                assert "${{ inputs." not in step.get("run", ""), path
        if path.name.startswith("deploy-"):
            assert set(workflow["on"]) == {"workflow_dispatch"}, path
            job = workflow["jobs"]["deploy"]
            assert job["if"].startswith("github.ref == 'refs/heads/"), path
            assert job["environment"]["name"], path
            assert workflow["concurrency"]["cancel-in-progress"] == "false", path
            assert workflow["permissions"].get("packages") == "read", path
    publisher = yaml.load((ROOT / ".github/workflows/build-and-publish.yml").read_text(), Loader=yaml.BaseLoader)
    assert publisher["jobs"]["publish"]["needs"] == "validate"
    print("Workflow syntax, action pins, permissions and deployment guards: PASS")


def validate_overlay(name):
    result = subprocess.run(["kubectl", "kustomize", str(ROOT / "infrastructure/kubernetes/overlays" / name)],
                            capture_output=True, text=True, check=True)
    documents = list(yaml.safe_load_all(result.stdout))
    namespace = f"hackathon-{name}"
    assert [doc["metadata"]["name"] for doc in documents if doc["kind"] == "Namespace"] == [namespace]
    resources = {(doc["kind"], doc["metadata"]["name"]): doc for doc in documents}
    assert len(resources) == len(documents), "Duplicate Kubernetes resources"
    for doc in documents:
        if doc["kind"] != "Namespace":
            assert doc["metadata"]["namespace"] == namespace
        if doc["kind"] == "Deployment":
            pod = doc["spec"]["template"]["spec"]
            assert pod["automountServiceAccountToken"] is False
            assert pod["securityContext"]["runAsNonRoot"] is True
            for container in pod["containers"]:
                assert container["securityContext"]["allowPrivilegeEscalation"] is False
                assert container["securityContext"]["capabilities"]["drop"] == ["ALL"]
                port = container["ports"][0]["containerPort"]
                for probe in ["startupProbe", "livenessProbe", "readinessProbe"]:
                    assert container[probe]["httpGet"]["port"] == port
                assert set(container["resources"]) == {"requests", "limits"}
        if doc["kind"] == "HorizontalPodAutoscaler":
            assert doc["spec"]["minReplicas"] <= doc["spec"]["maxReplicas"]
            assert ("Deployment", doc["spec"]["scaleTargetRef"]["name"]) in resources
    assert resources[("Service", "backend")]["spec"]["ports"][0]["targetPort"] == 8000
    assert resources[("Service", "backend")]["spec"]["ports"][0]["port"] == 8000
    assert resources[("Service", "frontend-service")]["spec"]["ports"][0]["targetPort"] == 8080
    ingress = resources[("Ingress", "hackathon-radar")]
    assert ingress["spec"]["rules"][0]["http"]["paths"][0]["pathType"] == "Prefix"
    assert ingress["spec"]["tls"]
    config = resources[("ConfigMap", "hackathon-app-config")]
    assert config["data"]["ENVIRONMENT"] == {"dev": "development", "test": "test", "staging": "staging", "prod": "production"}[name]
    print(f"Kustomize {name}: PASS ({len(documents)} resources)")


if __name__ == "__main__":
    validate_workflows()
    for environment in ["dev", "test", "staging", "prod"]:
        validate_overlay(environment)
    for path in (ROOT / "infrastructure").rglob("*.yaml"):
        list(yaml.safe_load_all(path.read_text()))
    print("Infrastructure YAML parse: PASS")

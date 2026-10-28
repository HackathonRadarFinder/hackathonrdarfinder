"""Render configuration, a one-shot migration job and workloads; no cluster IO."""
import copy
import os
from pathlib import Path
import re
import sys

import yaml
from verify_release import validate_tag


def dns_name(value):
    return (0 < len(value) <= 253 and all(
        re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
        for label in value.split(".")
    ))


def prepare(documents, env):
    tag = env["IMAGE_TAG"]
    validate_tag(tag)
    namespace = env["NAMESPACE"]
    if namespace not in {f"hackathon-{name}" for name in ["dev", "test", "staging", "prod"]}:
        raise ValueError("Unsupported namespace")
    host = env["INGRESS_HOST"]
    if not dns_name(host) or "." not in host or host.endswith(".invalid"):
        raise ValueError("Set INGRESS_HOST to the environment's real DNS hostname")
    tls = env["TLS_SECRET"]
    if not dns_name(tls):
        raise ValueError("Set TLS_SECRET to a valid Secret name")
    prefix = env["IMAGE_PREFIX"]
    if not re.fullmatch(r"ghcr\.io/[a-z0-9._-]+/[a-z0-9._-]+", prefix):
        raise ValueError("Invalid GHCR prefix")
    for document in documents:
        if document["kind"] == "Namespace":
            if document["metadata"]["name"] != namespace:
                raise ValueError("Rendered namespace mismatch")
            continue
        if document["metadata"].get("namespace") != namespace:
            raise ValueError("Rendered resource namespace mismatch")
        if document["kind"] == "Deployment":
            for container in document["spec"]["template"]["spec"]["containers"]:
                container["image"] = f"{prefix}/{container['name']}:{tag}"
        if document["kind"] == "Ingress":
            document["spec"]["rules"][0]["host"] = host
            document["spec"]["tls"] = [{"hosts": [host], "secretName": tls}]
    backend = next(doc for doc in documents if doc["kind"] == "Deployment" and doc["metadata"]["name"] == "backend")
    pod = copy.deepcopy(backend["spec"]["template"])
    pod["metadata"] = {"labels": {"app": "backend-migration"}}
    pod["spec"]["restartPolicy"] = "Never"
    container = pod["spec"]["containers"][0]
    for key in ["livenessProbe", "readinessProbe", "startupProbe", "ports"]:
        container.pop(key, None)
    container["command"] = ["python", "-m", "alembic", "upgrade", "head"]
    run = env["GITHUB_RUN_ID"]
    attempt = env["GITHUB_RUN_ATTEMPT"]
    if not run.isdigit() or not attempt.isdigit():
        raise ValueError("Invalid run identifier")
    name = f"backend-migrate-{tag[:12]}-{run}-{attempt}"
    if len(name) > 63:
        raise ValueError("Migration job name too long")
    job = {"apiVersion": "batch/v1", "kind": "Job", "metadata": {"name": name, "namespace": namespace},
           "spec": {"backoffLimit": 0, "activeDeadlineSeconds": 300, "ttlSecondsAfterFinished": 86400, "template": pod}}
    config = [doc for doc in documents if doc["kind"] == "ConfigMap"]
    workloads = [doc for doc in documents if doc["kind"] not in {"Namespace", "ConfigMap"}]
    return name, config, job, workloads


def main():
    documents = list(yaml.safe_load_all(Path(sys.argv[1]).read_text()))
    name, config, job, workloads = prepare(documents, os.environ)
    output = Path(sys.argv[2])
    output.mkdir(parents=True, exist_ok=True)
    for filename, docs in [("config.yaml", config), ("migration.yaml", [job]), ("workloads.yaml", workloads)]:
        (output / filename).write_text(yaml.safe_dump_all(docs, sort_keys=False), encoding="utf-8")
    with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as file:
        file.write(f"MIGRATION_JOB={name}\n")


if __name__ == "__main__":
    main()

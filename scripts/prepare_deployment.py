"""Render configuration, a one-shot migration job and workloads; no cluster IO."""
import copy
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs, urlsplit

import yaml
from verify_release import validate_tag


def dns_name(value):
    return (0 < len(value) <= 253 and all(
        re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
        for label in value.split(".")
    ))


PLACEHOLDER_SUFFIXES = (".invalid", ".example", ".example.com", ".example.org", ".localhost")
SUPABASE_SUFFIXES = (".supabase.co", ".supabase.com")


def public_https_host(value, name):
    """Return the host of a live https URL; messages never echo the value."""
    parts = urlsplit(value or "")
    host = parts.hostname or ""
    if (parts.scheme != "https" or parts.username or parts.password or not dns_name(host)
            or "." not in host or host.endswith(PLACEHOLDER_SUFFIXES)):
        raise ValueError(f"Set {name} to the live https URL without credentials")
    return host


def validate_platform(env):
    """Check Render, Cloudflare and Supabase settings; no network, no secret output."""
    render = public_https_host(env.get("RENDER_BACKEND_URL"), "RENDER_BACKEND_URL")
    cloudflare = public_https_host(env.get("CLOUDFLARE_FRONTEND_URL"), "CLOUDFLARE_FRONTEND_URL")
    if render == cloudflare:
        raise ValueError("RENDER_BACKEND_URL and CLOUDFLARE_FRONTEND_URL must be different hosts")
    database = urlsplit(env.get("DATABASE_URL") or "")
    host = database.hostname or ""
    if (database.scheme not in {"postgresql", "postgresql+psycopg", "postgres"}
            or not host.endswith(SUPABASE_SUFFIXES) or not database.path.strip("/")):
        raise ValueError("Set DATABASE_URL to the Supabase PostgreSQL connection string")
    if parse_qs(database.query).get("sslmode") != ["require"]:
        raise ValueError("DATABASE_URL must require TLS (sslmode=require)")
    if len(env.get("SECRET_KEY") or "") < 32:
        raise ValueError("Set SECRET_KEY to at least 32 characters")
    if env.get("ENVIRONMENT") != "production" or env.get("DEBUG", "false").lower() != "false":
        raise ValueError("Production requires ENVIRONMENT=production and DEBUG=false")
    if env.get("DISCOVERY_ENABLED", "").lower() != "true":
        raise ValueError("Set DISCOVERY_ENABLED=true so background workers run")
    if env.get("COLLECTOR_RAW_DATA_DIR") != "/app/collector-data/raw":
        raise ValueError("Set COLLECTOR_RAW_DATA_DIR=/app/collector-data/raw")
    try:
        interval = int(env.get("INGESTION_INTERVAL_SECONDS", "3600"))
        max_age = int(env.get("WORKER_MAX_AGE_SECONDS", "7200"))
    except ValueError:
        raise ValueError("Worker intervals must be whole seconds") from None
    if interval < 60 or max_age < 2 * interval:
        raise ValueError("WORKER_MAX_AGE_SECONDS must be at least twice INGESTION_INTERVAL_SECONDS")
    return {"platform_configuration_valid": True, "render_backend_host": render,
            "cloudflare_frontend_host": cloudflare, "supabase_tls_required": True,
            "ingestion_interval_seconds": interval, "worker_max_age_seconds": max_age}


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
    if sys.argv[1:] == ["--check-platform"]:
        try:
            print(json.dumps(validate_platform(os.environ)))
        except ValueError as error:
            print(f"Invalid platform configuration: {error}", file=sys.stderr)
            return 1
        return 0
    documents = list(yaml.safe_load_all(Path(sys.argv[1]).read_text()))
    name, config, job, workloads = prepare(documents, os.environ)
    output = Path(sys.argv[2])
    output.mkdir(parents=True, exist_ok=True)
    for filename, docs in [("config.yaml", config), ("migration.yaml", [job]), ("workloads.yaml", workloads)]:
        (output / filename).write_text(yaml.safe_dump_all(docs, sort_keys=False), encoding="utf-8")
    with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as file:
        file.write(f"MIGRATION_JOB={name}\n")


if __name__ == "__main__":
    raise SystemExit(main())

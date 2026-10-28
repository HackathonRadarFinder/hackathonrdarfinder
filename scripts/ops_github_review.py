"""Read-only PR/check inspection using Git's configured credential helper.

Credentials remain in memory and are never written or printed.
"""
import io
import json
import os
import re
import subprocess
import urllib.error
import urllib.request
import zipfile

REPO = "HackathonRadarFinder/hackathonrdarfinder"
credential = subprocess.run(
    ["git", "credential", "fill"],
    input="protocol=https\nhost=github.com\n\n", text=True,
    capture_output=True, check=False,
    env=dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="never"),
)
values = dict(line.split("=", 1) for line in credential.stdout.splitlines() if "=" in line)
token = values.get("password", "")


def fetch(path, binary=False):
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "OPS-001-read-only-review"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        with urllib.request.urlopen(urllib.request.Request(
            f"https://api.github.com/repos/{REPO}/{path}", headers=headers,
        ), timeout=30) as response:
            data = response.read()
            return data if binary else json.loads(data)
    except urllib.error.HTTPError as exc:
        print(f"API {path}: HTTP {exc.code}")
        return None


pr = fetch("pulls/64")
if pr:
    print(json.dumps({key: pr.get(key) for key in ["number", "title", "state", "changed_files", "mergeable_state", "html_url"]}))
    sha = pr["head"]["sha"]
    checks = fetch(f"commits/{sha}/check-runs")
    if checks:
        print(json.dumps([{
            key: check.get(key) for key in ["name", "status", "conclusion", "details_url"]
        } for check in checks["check_runs"]]))
    runs = fetch(f"actions/runs?head_sha={sha}&per_page=30")
    if runs:
        for run in runs["workflow_runs"]:
            print(json.dumps({key: run.get(key) for key in ["id", "name", "conclusion", "html_url"]}))
            if run["conclusion"] != "failure":
                continue
            logs = fetch(f"actions/runs/{run['id']}/logs", binary=True)
            if not logs:
                continue
            with zipfile.ZipFile(io.BytesIO(logs)) as archive:
                for name in archive.namelist():
                    content = archive.read(name).decode("utf-8", "replace")
                    matches = [line for line in content.splitlines() if re.search(
                        r"##\[error\]|ERROR:|ValidationError|Error:|error TS|failed|Failure", line,
                    )]
                    if matches:
                        clean = "\n".join(matches[:12]).replace(token, "[REDACTED]") if token else "\n".join(matches[:12])
                        print(f"LOG {name}:\n{clean[:3000]}")
    opened = fetch("pulls?state=open&per_page=100")
    if opened:
        for other in opened:
            files = fetch(f"pulls/{other['number']}/files?per_page=100")
            overlaps = [item["filename"] for item in files or [] if item["filename"].startswith(
                (".github/", "infrastructure/", "docs/operations/"),
            ) or item["filename"] in ["docker-compose.yml", "backend/requirements.txt", "backend/app/core/config.py"]]
            if overlaps:
                print(json.dumps({"pr": other["number"], "title": other["title"], "overlap": overlaps}))

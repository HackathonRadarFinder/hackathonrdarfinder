"""Read-only deployment provenance gate. Inputs are never evaluated as shell."""
import json
import os
import re
import subprocess
import urllib.request


def validate_tag(tag):
    if not re.fullmatch(r"[0-9a-f]{40}", tag):
        raise ValueError("image_tag must be a full lowercase commit SHA")


def validated_runs(runs, tag, branch):
    for path in [".github/workflows/ci.yml", ".github/workflows/build-and-publish.yml"]:
        matching = [run for run in runs if run["path"] == path
                    and run["head_sha"] == tag and run["head_branch"] == branch
                    and run["event"] == "push"]
        if not matching:
            return False
        latest = max(matching, key=lambda run: (run["run_number"], run["run_attempt"]))
        if latest["conclusion"] != "success":
            return False
    return True


def main():
    tag = os.environ["IMAGE_TAG"]
    validate_tag(tag)
    branch = os.environ["APPROVED_BRANCH"]
    if branch not in {"develop", "main"}:
        raise ValueError("Unsupported release branch")
    subprocess.run(["git", "merge-base", "--is-ancestor", tag, f"origin/{branch}"], check=True)
    request = urllib.request.Request(
        f"https://api.github.com/repos/{os.environ['GITHUB_REPOSITORY']}/actions/runs?head_sha={tag}&per_page=100",
        headers={"Authorization": f"Bearer {os.environ['GH_TOKEN']}",
                 "Accept": "application/vnd.github+json", "User-Agent": "OPS-001-release-gate"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        runs = json.load(response)["workflow_runs"]
    # Require a successful publisher on the reviewed target branch. Publisher
    # itself depends on the reusable CI suite, including Docker builds.
    if not validated_runs(runs, tag, branch):
        raise RuntimeError("Latest protected-branch CI and publish must both succeed")
    print("Release provenance verified")


if __name__ == "__main__":
    main()

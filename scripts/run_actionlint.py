"""Run a version-pinned official actionlint release after checksum verification."""
import hashlib
import io
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
import zipfile

VERSION = "1.7.7"
# SHA-256 values from the upstream v1.7.7 release checksum manifest.
RELEASE_SHA256 = {
    "actionlint_1.7.7_linux_amd64.tar.gz": "023070a287cd8cccd71515fedc843f1985bf96c436b7effaecce67290e7e0757",
    "actionlint_1.7.7_windows_amd64.zip": "7f12f1801bca3d480d67aaf7774f4c2a6359a3ca8eebe382c95c10c9704aa731",
}


def download_with_retry(url, attempts=4):
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(url, timeout=45) as response:
                return response.read()
        except (urllib.error.URLError, TimeoutError) as exc:
            if isinstance(exc, urllib.error.HTTPError) and exc.code not in {429, 500, 502, 503, 504}:
                raise
            if attempt == attempts - 1:
                raise
            delay = 2 ** attempt
            print(f"actionlint download temporarily unavailable; retrying in {delay}s", flush=True)
            time.sleep(delay)


def main():
    operating_system = {"Windows": "windows", "Linux": "linux"}.get(platform.system())
    if operating_system is None or platform.machine().lower() not in {"amd64", "x86_64"}:
        raise RuntimeError("This actionlint runner supports Windows/Linux amd64")
    extension = "zip" if operating_system == "windows" else "tar.gz"
    name = f"actionlint_{VERSION}_{operating_system}_amd64.{extension}"
    base = f"https://github.com/rhysd/actionlint/releases/download/v{VERSION}/"
    archive = download_with_retry(base + name)
    if hashlib.sha256(archive).hexdigest() != RELEASE_SHA256[name]:
        raise RuntimeError("actionlint release checksum mismatch")
    with tempfile.TemporaryDirectory(prefix="ops-actionlint-") as directory:
        root = Path(directory)
        # Extract only the named binary; no archive paths are trusted.
        binary = "actionlint.exe" if operating_system == "windows" else "actionlint"
        if extension == "zip":
            with zipfile.ZipFile(io.BytesIO(archive)) as bundle:
                executable = bundle.read(binary)
        else:
            with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as bundle:
                executable = bundle.extractfile(binary).read()
        target = root / binary
        target.write_bytes(executable)
        target.chmod(0o700)
        args = [str(target)]
        if not shutil.which("shellcheck"):
            print("ShellCheck unavailable; actionlint runs without optional shell analysis")
            args.append("-shellcheck=")
        repo = Path(__file__).resolve().parents[1]
        args += [str(path) for path in (repo / ".github/workflows").glob("*.yml")]
        subprocess.run(args, cwd=repo, check=True)
        print(f"actionlint {VERSION}: PASS")


if __name__ == "__main__":
    main()

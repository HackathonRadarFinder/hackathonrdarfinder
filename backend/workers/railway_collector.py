"""Initialize only the collector mount, then run discovery without root privileges."""
import os
from pathlib import Path


def main():
    mount = Path("/app/collector-data")
    if mount.is_symlink() or mount.resolve() != mount:
        raise RuntimeError("Collector mount must be /app/collector-data")
    if os.geteuid() == 0:
        # Railway mounts volumes as root. Never recursively chown user content.
        os.chown(mount, 10001, 10001)
        os.setgroups([])
        os.setgid(10001)
        os.setuid(10001)
    if os.geteuid() != 10001 or not os.access(mount, os.W_OK):
        raise RuntimeError("Collector volume must be writable by UID 10001")
    if os.environ.get("COLLECTOR_SNAPSHOT_DIR") != str(mount):
        raise RuntimeError("Set COLLECTOR_SNAPSHOT_DIR=/app/collector-data")
    if os.environ.get("COLLECTOR_RAW_DATA_DIR") != str(mount / "raw"):
        raise RuntimeError("Set COLLECTOR_RAW_DATA_DIR=/app/collector-data/raw")
    args = ["python", "-m", "workers.discovery", "--watch"]
    if os.environ.get("COLLECTION_ALLOW_LIVE", "").lower() == "true":
        args.append("--allow-live")
    os.execvp(args[0], args)


if __name__ == "__main__":
    main()

"""Opt-in one-shot raw collection with durable due times and source claims.

The state database is separate from the application's database. No import or
invocation opens PostgreSQL, ingests events, sends email or starts a background
thread. A crashed claim remains running until an operator reconciles it.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import time
from uuid import uuid4

from .config.loader import ConfigError, Settings, load_sources
from .manager import CollectorManager
from .models import Source, validate_source_id
from .monitoring.logger import setup_logging
from .storage.factory import create_storage


def utc(value: datetime) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("Scheduler time must include a timezone")
    return value.astimezone(timezone.utc)


def _text(value) -> bool:
    return (isinstance(value, str) and 0 < len(value.strip()) <= 1000
            and not any(ord(c) < 32 or ord(c) == 127 for c in value))


@dataclass(frozen=True)
class ScheduledJob:
    source_id: str
    interval_seconds: int
    enabled: bool = False
    adapter_version: str = ""
    approval: dict = field(default_factory=dict)

    def __post_init__(self):
        validate_source_id(self.source_id)
        if type(self.enabled) is not bool:
            raise ConfigError("Schedule enabled must be a boolean")
        if type(self.interval_seconds) is not int or not 60 <= self.interval_seconds <= 604800:
            raise ConfigError("Schedule interval must be 60 to 604800 seconds")
        if not isinstance(self.approval, dict):
            raise ConfigError("Schedule approval must be an object")


def load_schedule(path: Path) -> tuple[bool, list[ScheduledJob]]:
    try:
        if path.stat().st_size > 1_000_000:
            raise ConfigError("Schedule configuration exceeds size limit")
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if (not isinstance(payload, dict) or type(payload.get("enabled", False)) is not bool
                or not isinstance(payload.get("jobs"), list) or len(payload["jobs"]) > 100):
            raise ConfigError("Invalid schedule configuration")
        jobs = [ScheduledJob(**entry) for entry in payload["jobs"]]
        if len({job.source_id for job in jobs}) != len(jobs):
            raise ConfigError("Duplicate schedule source")
        return payload.get("enabled", False), jobs
    except (OSError, ValueError, TypeError) as exc:
        raise ConfigError("Unable to load valid schedule configuration") from exc


def policy_reason(job: ScheduledJob, source: Source, now: datetime) -> str | None:
    """A human approval record supplements, never bypasses, collector policy."""
    if not source.enabled:
        return "source_disabled"
    if not source.tos_allows_scraping or not _text(source.tos_note):
        return "permission_missing"
    if not _text(job.adapter_version):
        return "adapter_unreviewed"
    approval = job.approval
    if not all(_text(approval.get(key)) for key in ("owner", "basis", "reference")):
        return "approval_missing"
    try:
        reviewed = utc(datetime.fromisoformat(approval["reviewed_at"].replace("Z", "+00:00")))
        expires = utc(datetime.fromisoformat(approval["expires_at"].replace("Z", "+00:00")))
    except (KeyError, ValueError, TypeError, AttributeError):
        return "approval_invalid"
    if reviewed > now or expires <= reviewed:
        return "approval_invalid"
    if expires <= now:
        return "approval_expired"
    return None


class ScheduleState:
    def __init__(self, path: Path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS source_schedule (
                source_id TEXT PRIMARY KEY, next_run_at TEXT NOT NULL,
                running INTEGER NOT NULL DEFAULT 0 CHECK (running IN (0, 1))
            );
            CREATE TABLE IF NOT EXISTS collection_runs (
                id INTEGER PRIMARY KEY, source_id TEXT NOT NULL,
                started_at TEXT NOT NULL, ended_at TEXT,
                status TEXT NOT NULL CHECK (status IN ('running', 'success', 'skipped', 'blocked', 'failed')),
                reason TEXT, policy_decision TEXT NOT NULL, adapter_version TEXT NOT NULL,
                http_status INTEGER, attempts INTEGER NOT NULL DEFAULT 0,
                content_type TEXT, checksum TEXT, latency_ms INTEGER,
                storage_location TEXT
            );
            CREATE INDEX IF NOT EXISTS collection_runs_source ON collection_runs(source_id, started_at);
            CREATE TABLE IF NOT EXISTS scheduler_lock (
                singleton INTEGER PRIMARY KEY CHECK (singleton = 1), owner TEXT NOT NULL
            );
        """)

    def close(self):
        self.db.close()

    def acquire(self, owner: str) -> bool:
        with self.db:
            cursor = self.db.execute("INSERT OR IGNORE INTO scheduler_lock(singleton, owner) VALUES (1, ?)", (owner,))
        return cursor.rowcount == 1

    def release(self, owner: str):
        with self.db:
            self.db.execute("DELETE FROM scheduler_lock WHERE singleton = 1 AND owner = ?", (owner,))

    def claim(self, job: ScheduledJob, now: datetime, reason: str | None) -> int | None:
        now = utc(now)
        stamp = now.isoformat()
        try:
            self.db.execute("BEGIN IMMEDIATE")
            row = self.db.execute("SELECT * FROM source_schedule WHERE source_id = ?", (job.source_id,)).fetchone()
            if row is not None and (row["running"] or row["next_run_at"] > stamp):
                self.db.rollback()
                return None
            self.db.execute("""INSERT INTO source_schedule(source_id, next_run_at, running) VALUES (?, ?, 1)
                ON CONFLICT(source_id) DO UPDATE SET next_run_at = excluded.next_run_at, running = 1""",
                (job.source_id, (now + timedelta(seconds=job.interval_seconds)).isoformat()))
            cursor = self.db.execute("""INSERT INTO collection_runs
                (source_id, started_at, status, policy_decision, adapter_version)
                VALUES (?, ?, 'running', ?, ?)""",
                (job.source_id, stamp, reason or "approved_pending_robots", job.adapter_version))
            self.db.commit()  # Durable claim before any network request.
            return cursor.lastrowid
        except BaseException:
            self.db.rollback()
            raise

    def finish(self, run_id: int, *, status: str, now: datetime, reason: str | None = None,
               result=None, latency_ms: int = 0):
        checksum = None
        if result is not None and result.status == "success" and result.raw_content is not None:
            checksum = hashlib.sha256(result.raw_content.encode("utf-8")).hexdigest()
        policy = (reason if result is None else "robots_allowed" if result.robots_allowed
                  else "robots_denied" if result.robots_allowed is False else "collector_refused")
        with self.db:
            row = self.db.execute("SELECT source_id FROM collection_runs WHERE id = ? AND status = 'running'",
                                  (run_id,)).fetchone()
            if row is None:
                raise ValueError("Run is not active")
            self.db.execute("""UPDATE collection_runs SET ended_at = ?, status = ?, reason = ?,
                policy_decision = ?, http_status = ?, attempts = ?, content_type = ?, checksum = ?,
                latency_ms = ?, storage_location = ? WHERE id = ?""",
                (utc(now).isoformat(), status, reason, policy,
                 result.http_status if result else None, result.attempts if result else 0,
                 result.content_type if result else None, checksum, latency_ms,
                 result.storage_location if result else None, run_id))
            self.db.execute("UPDATE source_schedule SET running = 0 WHERE source_id = ?", (row["source_id"],))


def run_due(jobs: list[ScheduledJob], sources: list[Source], state: ScheduleState, manager,
            *, clock=lambda: datetime.now(timezone.utc)) -> dict[str, int]:
    by_id = {source.source_id: source for source in sources}
    if any(job.source_id not in by_id for job in jobs):
        raise ConfigError("Scheduled source does not exist in source configuration")
    counts = {key: 0 for key in ("success", "skipped", "blocked", "failed", "not_due")}
    owner = uuid4().hex
    if not state.acquire(owner):
        counts["not_due"] = sum(job.enabled for job in jobs)
        return counts
    try:
        return _run_claimed(jobs, by_id, state, manager, counts, clock)
    finally:
        state.release(owner)


def _run_claimed(jobs, by_id, state, manager, counts, clock):
    for job in jobs:
        if not job.enabled:
            continue
        source = by_id[job.source_id]
        now = utc(clock())
        reason = policy_reason(job, source, now)
        run_id = state.claim(job, now, reason)
        if run_id is None:
            counts["not_due"] += 1
            continue
        if reason:
            state.finish(run_id, status="skipped", now=utc(clock()), reason=reason)
            counts["skipped"] += 1
            continue
        started = time.monotonic()
        try:
            result = manager.collect(source)
            status = result.status
            if status not in ("success", "skipped", "blocked", "failed"):
                raise ValueError("Invalid collector outcome")
            # Do not persist exception text, response content or query strings.
            reason = None if status == "success" else "collector_" + status
            state.finish(run_id, status=status, now=utc(clock()), reason=reason, result=result,
                         latency_ms=int((time.monotonic() - started) * 1000))
        except Exception:
            status = "failed"
            state.finish(run_id, status=status, now=utc(clock()), reason="collector_exception",
                         latency_ms=int((time.monotonic() - started) * 1000))
        counts[status] += 1
    return counts


class _DeferredCollector:
    """Do not discover storage credentials or initialize clients before approval."""
    def __init__(self, settings: Settings):
        self.settings = settings
        self.manager = None

    def collect(self, source):
        if self.manager is None:
            setup_logging(self.settings.log_dir, self.settings.log_level)
            self.manager = CollectorManager(self.settings, create_storage(self.settings))
        return self.manager.collect(source)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("config/schedule.json"))
    parser.add_argument("--sources", type=Path, default=Path("config/sources.json"))
    parser.add_argument("--state", type=Path, default=Path("data/scheduler.sqlite3"))
    parser.add_argument("--run", action="store_true", help="Opt in to due approved collection")
    args = parser.parse_args(argv)
    state = None
    try:
        enabled, jobs = load_schedule(args.config)
        if not enabled or not args.run:
            print(json.dumps({"enabled": enabled, "executed": False}))
            return 0
        sources = load_sources(args.sources, enabled_only=False)
        if any(job.source_id not in {source.source_id for source in sources} for job in jobs):
            raise ConfigError("Scheduled source does not exist")
        settings = Settings.from_env()  # Do not load the application's .env or database credentials.
        manager = _DeferredCollector(settings)
        state = ScheduleState(args.state)
        counts = run_due(jobs, sources, state, manager)
        print(json.dumps({"executed": True, **counts}))
        return 1 if counts["failed"] else 0
    except Exception:
        print("Scheduled collection failed; inspect approved configuration and run history.", file=sys.stderr)
        return 2
    finally:
        if state is not None:
            state.close()

"""Health report for maintainer alerts: database connectivity and worker freshness.

The plain `/health` route in `app.main` stays a cheap liveness probe for the
platform. This route (`/api/v1/health`) additionally checks the database and
how recently a background worker finished a discovery run, and answers 503 when
either check fails so an external monitor can alert on the status code alone.
"""
from datetime import datetime, timezone
import os

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings

router = APIRouter()

DEFAULT_WORKER_MAX_AGE_SECONDS = 7200  # two missed hourly passes
MIN_WORKER_MAX_AGE_SECONDS = 60
MAX_WORKER_MAX_AGE_SECONDS = 86400


def worker_max_age_seconds():
    try:
        value = int(os.environ.get("WORKER_MAX_AGE_SECONDS", DEFAULT_WORKER_MAX_AGE_SECONDS))
    except ValueError:
        return DEFAULT_WORKER_MAX_AGE_SECONDS
    return min(max(value, MIN_WORKER_MAX_AGE_SECONDS), MAX_WORKER_MAX_AGE_SECONDS)


def worker_freshness_required():
    return os.environ.get("WORKER_FRESHNESS_REQUIRED", "").lower() == "true"


def database_status(engine):
    """Return 'connected' or 'unavailable'; never expose driver details."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return "connected"
    except SQLAlchemyError:
        return "unavailable"


def worker_status(engine, now):
    """Report the most recent finished discovery run and whether it is fresh."""
    from app.models.discovery import DiscoveryRun

    max_age = worker_max_age_seconds()
    report = {
        "status": "unknown",
        "last_run_at": None,
        "last_run_status": None,
        "age_seconds": None,
        "max_age_seconds": max_age,
    }
    try:
        with engine.connect() as connection:
            row = connection.execute(
                select(DiscoveryRun.finished_at, DiscoveryRun.status)
                .where(DiscoveryRun.finished_at.is_not(None))
                .order_by(DiscoveryRun.finished_at.desc())
                .limit(1)
            ).first()
    except SQLAlchemyError:
        return report
    if row is None:
        return report
    finished_at, last_status = row
    if finished_at.tzinfo is None:
        finished_at = finished_at.replace(tzinfo=timezone.utc)
    age = max(0, int((now - finished_at).total_seconds()))
    report.update(
        status="fresh" if age <= max_age else "stale",
        last_run_at=finished_at.isoformat(),
        last_run_status=last_status,
        age_seconds=age,
    )
    return report


def build_health_report(engine, now=None):
    now = now or datetime.now(timezone.utc)
    database = database_status(engine)
    workers = (
        worker_status(engine, now)
        if database == "connected"
        else {"status": "unknown", "last_run_at": None, "last_run_status": None,
              "age_seconds": None, "max_age_seconds": worker_max_age_seconds()}
    )
    workers_failing = workers["status"] == "stale" or (
        workers["status"] == "unknown" and worker_freshness_required()
    )
    if database != "connected":
        status = "unhealthy"
    elif workers_failing:
        status = "degraded"
    else:
        status = "healthy"
    return {
        "status": status,
        "service": "hackathon-radar-api",
        "version": settings.APP_VERSION,
        "database": database,
        "workers": workers,
    }


@router.get("/health")
def health_check():
    from app.core import database

    report = build_health_report(database.engine)
    code = 200 if report["status"] == "healthy" else 503
    return JSONResponse(status_code=code, content=report)

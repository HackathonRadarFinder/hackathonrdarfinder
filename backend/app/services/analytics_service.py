"""INT-05: read-only platform analytics.

Tables/columns added later by the v4.1 migrations (jobs, hackathons.category)
are detected at run time. If they are missing the metric is reported as
unavailable instead of a made-up zero.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, inspect, select, text
from sqlalchemy.orm import Session

from app.models.hackathon import Hackathon
from app.models.institution import Institution
from app.services.database import database_operation

JOB_WINDOW_DAYS = 14


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _columns(db: Session, table: str) -> set[str]:
    inspector = inspect(db.get_bind())
    if not inspector.has_table(table):
        return set()
    return {column["name"] for column in inspector.get_columns(table)}


def _live_filter(columns: set[str]) -> str:
    """Live = not already ended and not cancelled (when those columns exist)."""
    parts = []
    if "end_date" in columns:
        parts.append("(end_date IS NULL OR end_date >= :now)")
    if "status" in columns:
        parts.append("(status IS NULL OR status != 'cancelled')")
    return " AND ".join(parts) or "1=1"


def _live_hackathons(db: Session, now: datetime) -> int:
    where = _live_filter(_columns(db, "hackathons"))
    return int(db.execute(text(f"SELECT COUNT(*) FROM hackathons WHERE {where}"), {"now": now}).scalar_one())


def _hackathons_by_category(db: Session, now: datetime):
    columns = _columns(db, "hackathons")
    if "category" not in columns:
        return None, "unavailable_until_category_migration"
    rows = db.execute(text(
        f"SELECT category, COUNT(*) FROM hackathons WHERE {_live_filter(columns)} GROUP BY category"
    ), {"now": now}).all()
    result = {}
    for category, count in rows:
        label = category if category else "unknown"
        result[label] = result.get(label, 0) + count
    return dict(sorted(result.items())), "available"


def _active_jobs(db: Session, now: datetime) -> dict:
    columns = _columns(db, "jobs")
    if not columns:
        return {"value": None, "status": "unavailable",
                "reason": "jobs table does not exist yet"}
    # Spec: show a job for <= 14 days after first verified publication,
    # or until its earlier known closing date.
    published = next((c for c in ("first_published_at", "published_at", "posted_at")
                      if c in columns), None)
    if published is None:
        return {"value": None, "status": "unavailable",
                "reason": "jobs table has no publication timestamp column"}
    closes = next((c for c in ("closes_at", "closing_date", "deadline") if c in columns), None)
    sql = f"SELECT COUNT(*) FROM jobs WHERE {published} >= :oldest"
    params = {"oldest": now - timedelta(days=JOB_WINDOW_DAYS)}
    if closes:
        sql += f" AND ({closes} IS NULL OR {closes} >= :now)"
        params["now"] = now
    count = db.execute(text(sql), params).scalar_one()
    return {"value": int(count), "status": "available", "reason": None}


SUCCESS_VALUES = ("success", "succeeded", "completed", "ok")


def _last_successful_ingest_by_area(db: Session):
    """Latest successful ingest_runs row per area. Column names are tolerant until INT-01 fixes them."""
    columns = _columns(db, "ingest_runs")
    if not columns:
        return None, "unavailable_until_ingest_runs_migration"
    area = next((c for c in ("area", "kind", "source_type", "run_type", "entity") if c in columns), None)
    finished = next((c for c in ("finished_at", "completed_at", "ended_at", "started_at") if c in columns), None)
    if area is None or finished is None:
        return None, "unavailable_until_ingest_runs_migration"
    where, params = "", {}
    if "status" in columns:
        names = ", ".join(f":s{i}" for i in range(len(SUCCESS_VALUES)))
        where = f"WHERE status IN ({names})"
        params = {f"s{i}": value for i, value in enumerate(SUCCESS_VALUES)}
    rows = db.execute(text(
        f"SELECT {area}, MAX({finished}) FROM ingest_runs {where} GROUP BY {area}"), params).all()
    result = {str(name): when for name, when in rows if name is not None and when is not None}
    return (result, "available") if result else (None, "no_successful_runs")


def get_analytics_summary(db: Session) -> dict:
    now = _now()
    with database_operation(db):
        total = db.scalar(select(func.count()).select_from(Hackathon)) or 0
        upcoming = db.scalar(select(func.count()).select_from(Hackathon)
                             .where(Hackathon.start_date >= now)) or 0
        by_category, category_status = _hackathons_by_category(db, now)
        colleges = db.scalar(select(func.count()).select_from(Institution)) or 0
        latest = db.scalar(select(func.max(Hackathon.scraped_at)))
        last_24h = db.scalar(select(func.count()).select_from(Hackathon)
                             .where(Hackathon.scraped_at >= now - timedelta(hours=24))) or 0
        last_7d = db.scalar(select(func.count()).select_from(Hackathon)
                            .where(Hackathon.scraped_at >= now - timedelta(days=7))) or 0
        jobs = _active_jobs(db, now)
        live = _live_hackathons(db, now)
        ingest_by_area, ingest_status = _last_successful_ingest_by_area(db)
    return {
        "generated_at": now,
        "hackathons_total": total,
        "hackathons_upcoming": upcoming,
        "hackathons_live": live,
        "hackathons_by_category": by_category,
        "hackathons_by_category_status": category_status,
        "active_jobs_14d": jobs,
        "indexed_colleges": colleges,
        "freshness": {
            "latest_hackathon_collected_at": latest,
            "hackathons_collected_last_24h": last_24h,
            "hackathons_collected_last_7d": last_7d,
            "status": "available" if latest else "no_collection_data",
            "last_successful_ingest_by_area": ingest_by_area,
            "ingest_runs_status": ingest_status,
        },
    }

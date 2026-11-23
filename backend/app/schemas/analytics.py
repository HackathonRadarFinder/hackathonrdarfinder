"""INT-05 response shapes for the public platform analytics summary."""
from datetime import datetime

from pydantic import BaseModel


class CountOrUnknown(BaseModel):
    """A number, or null with a reason. Never a guessed zero (SRS NFR-05)."""
    value: int | None
    status: str  # "available" or "unavailable"
    reason: str | None = None


class FreshnessStats(BaseModel):
    latest_hackathon_collected_at: datetime | None
    hackathons_collected_last_24h: int
    hackathons_collected_last_7d: int
    status: str  # "available" or "no_collection_data"
    last_successful_ingest_by_area: dict[str, datetime] | None
    ingest_runs_status: str  # "available", "no_successful_runs" or "unavailable_until_ingest_runs_migration"


class AnalyticsSummary(BaseModel):
    generated_at: datetime
    hackathons_total: int
    hackathons_upcoming: int
    hackathons_live: int
    hackathons_by_category: dict[str, int] | None
    hackathons_by_category_status: str
    active_jobs_14d: CountOrUnknown
    indexed_colleges: int
    freshness: FreshnessStats

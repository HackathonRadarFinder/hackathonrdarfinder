"""Validated event writes with the legacy organization-name input retained."""
from datetime import date, datetime, timezone
import re
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints, field_validator, model_validator

from app.schemas.hackathon import HackathonCreate
from app.schemas.responses import DataResponse

RequiredName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]


class EventCreate(HackathonCreate):
    title: RequiredName
    organization: RequiredName | None = None
    organization_id: int | None = Field(default=None, strict=True, gt=0, le=2_147_483_647)
    location: str | None = Field(default=None, max_length=255)
    mode: str | None = Field(default=None, max_length=50)
    prize: str | None = Field(default=None, max_length=255)
    source: str | None = Field(default=None, max_length=100)
    url: HttpUrl | None = Field(default=None, max_length=500)

    @field_validator("start_date", "end_date", "registration_deadline", "scraped_at")
    @classmethod
    def normalize_datetime(cls, value: datetime | None) -> datetime | None:
        # Existing event columns store timezone-naive datetimes; use UTC for
        # offset-bearing inputs instead of silently discarding their offset.
        if value is not None and value.tzinfo is not None:
            try:
                return value.astimezone(timezone.utc).replace(tzinfo=None)
            except OverflowError:
                raise ValueError("Datetime is outside supported UTC range") from None
        return value

    @model_validator(mode="after")
    def validate_references_and_dates(self):
        if (self.organization is None) == (self.organization_id is None):
            raise ValueError("Provide exactly one of organization or organization_id")
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must not precede start_date")
        return self


class EventResponse(BaseModel):
    # Reads remain tolerant of historical scraper data. Write constraints above
    # must not turn otherwise readable legacy rows into response errors.
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    organization_id: int | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    registration_deadline: datetime | None = None
    location: str | None = None
    mode: str | None = None
    prize: str | None = None
    description: str | None = None
    url: str | None = None
    source: str | None = None
    scraped_at: datetime | None = None


class EventListParams(BaseModel):
    """Any supported query parameter opts into pagination; omitted values default later."""

    page: int | None = Field(default=None, ge=1, le=2_147_483_647)
    q: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)] | None = None
    page_size: int | None = Field(default=None, ge=1, le=100)
    location: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
    ] | None = None
    mode: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)
    ] | None = None
    organization_id: int | None = Field(default=None, ge=1, le=2_147_483_647)
    start_from: date | None = Field(default=None, description="Inclusive event start date in UTC (YYYY-MM-DD).")
    start_to: date | None = Field(default=None, description="Inclusive event start date in UTC (YYYY-MM-DD).")

    @field_validator("start_from", "start_to", mode="before")
    @classmethod
    def require_calendar_date(cls, value):
        if value is None or type(value) is date:
            return value
        # Pydantic otherwise also accepts numeric epoch values or midnight
        # timestamps. A date filter must not silently reinterpret either.
        if not isinstance(value, str) or re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value) is None:
            raise ValueError("Use an ISO calendar date in YYYY-MM-DD format")
        return value

    @model_validator(mode="after")
    def validate_date_window(self):
        if self.start_from is not None and self.start_to is not None and self.start_from > self.start_to:
            raise ValueError("start_to must not precede start_from")
        return self


class EventListResponse(DataResponse[list[EventResponse]]):
    """Add pagination metadata while retaining the established message/data envelope."""

    total: int = Field(ge=0)
    page: int = Field(ge=1, le=2_147_483_647)
    page_size: int = Field(ge=1, le=100)

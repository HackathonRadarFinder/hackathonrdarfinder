"""Validated event writes with the legacy organization-name input retained."""
from datetime import datetime, timezone
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


class EventListResponse(DataResponse[list[EventResponse]]):
    """Add pagination metadata while retaining the established message/data envelope."""

    total: int = Field(ge=0)
    page: int = Field(ge=1, le=2_147_483_647)
    page_size: int = Field(ge=1, le=100)

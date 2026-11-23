"""Validated event writes with the legacy organization-name input retained."""
from datetime import date, datetime, timezone as dt_timezone
import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, StringConstraints, field_validator, model_validator

from app.schemas.hackathon import HackathonCreate
from app.schemas.responses import DataResponse

RequiredName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)]

# --- BAC-02: v4.1 types -----------------------------------------------------
CategoryType = Literal["college", "corporate", "community", "government", "startup"]
LifecycleState = Literal["upcoming", "active", "completed", "cancelled"]
Tag = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=50)]


class OrganizerContact(BaseModel):
    """Missing contact details are returned as "unknown", never guessed."""

    name: str = "unknown"
    designation: str = "unknown"
    email: str = "unknown"
    phone: str = "unknown"

    @field_validator("name", "designation", "email", "phone", mode="before")
    @classmethod
    def fill_unknown(cls, value):
        if value is None or (isinstance(value, str) and not value.strip()):
            return "unknown"
        return value.strip() if isinstance(value, str) else value


class EventCreate(HackathonCreate):
    state: str | None = Field(default=None, max_length=100)
    institution_id: int | None = Field(default=None, strict=True, gt=0)
    registration_url: HttpUrl | None = Field(default=None, max_length=500)
    eligibility: str | None = Field(default=None, max_length=5000)
    title: RequiredName
    organization: RequiredName | None = None
    organization_id: int | None = Field(default=None, strict=True, gt=0, le=2_147_483_647)
    location: str | None = Field(default=None, max_length=255)
    mode: str | None = Field(default=None, max_length=50)
    prize: str | None = Field(default=None, max_length=255)
    source: str | None = Field(default=None, max_length=100)
    url: HttpUrl | None = Field(default=None, max_length=500)
    # --- BAC-02: v4.1 fields (all optional so old clients keep working) ---
    category: CategoryType | None = None
    tags: list[Tag] = Field(default_factory=list, max_length=20)
    timezone: str | None = Field(default=None, max_length=64)
    country: str | None = Field(default=None, max_length=100)
    city: str | None = Field(default=None, max_length=100)
    fees: str | None = Field(default=None, max_length=100)
    lifecycle_state: LifecycleState = "upcoming"
    contacts: OrganizerContact = Field(default_factory=OrganizerContact)

    @field_validator("start_date", "end_date", "registration_deadline", "scraped_at")
    @classmethod
    def normalize_datetime(cls, value: datetime | None) -> datetime | None:
        # Existing event columns store timezone-naive datetimes; use UTC for
        # offset-bearing inputs instead of silently discarding their offset.
        if value is not None and value.tzinfo is not None:
            try:
                return value.astimezone(dt_timezone.utc).replace(tzinfo=None)
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


class ProviderAttribution(BaseModel):
    provider: str
    provider_id: str
    provider_url: str
    attribution: str
    method: str
    original_platform: str
    original_url: str
    acquired_at: str
    source_refreshed_at: str
    api_record_sha256: str


class EventResponse(BaseModel):
    # Reads remain tolerant of historical scraper data. Write constraints above
    # must not turn otherwise readable legacy rows into response errors.
    model_config = ConfigDict(from_attributes=True)
    id: int
    state: str | None = None
    institution_id: int | None = None
    registration_url: str | None = None
    eligibility: str | None = None
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
    acquisition: ProviderAttribution | None = None
    # --- BAC-02: v4.1 fields ---
    category: str | None = None
    tags: list[str] = Field(default_factory=list)
    timezone: str | None = None
    country: str | None = None
    city: str | None = None
    fees: str | None = None
    lifecycle_state: str | None = None
    contacts: OrganizerContact = Field(default_factory=OrganizerContact)

    @field_validator("tags", mode="before")
    @classmethod
    def tags_default(cls, value):
        return [] if value is None else value

    @field_validator("contacts", mode="before")
    @classmethod
    def contacts_default(cls, value):
        return {} if value is None else value


class EventListParams(BaseModel):
    """Any supported query parameter opts into pagination; omitted values default later."""

    state: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)] | None = None
    institution_id: int | None = Field(default=None, ge=1, le=2_147_483_647)
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
    sort: Literal['id', 'title', 'start_date', 'deadline'] | None = None
    period: Literal['upcoming', 'past'] | None = None
    deadline_from: date | None = None
    deadline_to: date | None = None
    start_from: date | None = Field(default=None, description="Inclusive event start date in UTC (YYYY-MM-DD).")
    start_to: date | None = Field(default=None, description="Inclusive event start date in UTC (YYYY-MM-DD).")
    # --- BAC-02: v4.1 filters ---
    category: CategoryType | None = None
    tag: Tag | None = None
    lifecycle_state: LifecycleState | None = None
    country: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)] | None = None
    city: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)] | None = None

    @field_validator("start_from", "start_to", "deadline_from", "deadline_to", mode="before")
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
        if self.deadline_from is not None and self.deadline_to is not None and self.deadline_from > self.deadline_to:
            raise ValueError("deadline_to must not precede deadline_from")
        return self


class EventListResponse(DataResponse[list[EventResponse]]):
    """Add pagination metadata while retaining the established message/data envelope."""

    total: int = Field(ge=0)
    page: int = Field(ge=1, le=2_147_483_647)
    page_size: int = Field(ge=1, le=100)
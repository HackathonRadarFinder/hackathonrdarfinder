from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class SourceCreate(BaseModel):
    source_name: str = Field(min_length=1, max_length=100)

    base_url: HttpUrl

    source_type: Literal["API", "static", "dynamic"]

    tier: int = Field(default=1, ge=1)

    crawl_frequency: str = Field(
        default="24h",
        min_length=2,
        max_length=20
    )

    priority: int = Field(
        default=1,
        ge=1
    )

    created_by: str = Field(
        min_length=1,
        max_length=100
    )


class SourceUpdate(BaseModel):
    source_name: str | None = Field(
        default=None,
        min_length=1,
        max_length=100
    )

    source_type: Literal["API", "static", "dynamic"] | None = None

    tier: int | None = Field(
        default=None,
        ge=1
    )

    crawl_frequency: str | None = Field(
        default=None,
        min_length=2,
        max_length=20
    )

    priority: int | None = Field(
        default=None,
        ge=1
    )

    is_active: bool | None = None


class SourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source_id: int
    source_name: str
    base_url: str
    source_type: str
    tier: int
    crawl_frequency: str
    priority: int
    is_active: bool
    robots_txt_allowed: bool
    robots_txt_status: str
    last_crawled_at: datetime | None
    created_by: str
    created_at: datetime
    updated_at: datetime
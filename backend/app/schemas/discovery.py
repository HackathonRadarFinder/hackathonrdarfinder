from datetime import datetime, timezone
from typing import Literal
from urllib.parse import urlsplit
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator


class SourcePolicy(BaseModel):
    model_config = ConfigDict(extra='forbid')
    key: str = Field(pattern=r'^[a-z0-9][a-z0-9_-]{0,99}$')
    name: str = Field(min_length=1, max_length=150)
    adapter: Literal['curated-v1', 'unstop-v1', 'official-html-v1', 'rss-v1', 'sitemap-v1', 'events-json-v1']
    institution_id: int | None = Field(default=None, strict=True, gt=0)
    url: str = Field(max_length=500)
    enabled: StrictBool = False
    interval_seconds: int = Field(default=21600, ge=300, le=604800)
    owner: str = Field(min_length=1, max_length=100)
    basis: str = Field(min_length=1, max_length=500)
    reference: str = Field(min_length=1, max_length=500)
    reviewed_at: datetime
    expires_at: datetime
    terms_permit: StrictBool = False

    @field_validator('reviewed_at', 'expires_at')
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None:
            raise ValueError('Approval dates require a timezone')
        return value.astimezone(timezone.utc)

    @field_validator('name', 'owner', 'basis', 'reference')
    @classmethod
    def text(cls, value):
        if not value.strip() or any(ord(c) < 32 for c in value):
            raise ValueError('Nonblank text without controls required')
        return value.strip()

    @model_validator(mode='after')
    def valid_policy(self):
        if self.expires_at <= self.reviewed_at:
            raise ValueError('Approval expiry must follow review')
        parts = urlsplit(self.url)
        if self.adapter == 'curated-v1':
            if self.url != 'curated://mvp-20261013':
                raise ValueError('Only the fixed reviewed local manifest is supported')
        elif self.adapter != 'unstop-v1':
            from app.schemas.institution import public_https
            public_https(self.url)
            if self.adapter == 'official-html-v1' and self.institution_id is None:
                raise ValueError('Official pages require a verified institution')
        elif (parts.scheme != 'https' or parts.hostname != 'unstop.com'
              or parts.path != '/api/public/opportunity/search-result'
              or parts.username or parts.password or parts.port or parts.fragment
              or any(ord(c) <= 32 for c in self.url)):
            raise ValueError('Only the governed HTTPS Unstop search endpoint is supported')
        return self

"""Operator-reviewed export contract; import never implies permission to crawl."""
from datetime import datetime, timezone
from typing import Literal
from urllib.parse import urlsplit
import ipaddress
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator


def public_https(value):
    parts = urlsplit(value)
    if (parts.scheme != 'https' or not parts.hostname or parts.username or parts.password
            or parts.port not in (None, 443) or parts.fragment or '\\' in value
            or any(ord(c) <= 32 or ord(c) == 127 for c in value)):
        raise ValueError('Credential-free public HTTPS URL required')
    host = parts.hostname.lower()
    try:
        if not ipaddress.ip_address(host).is_global:
            raise ValueError('Private addresses forbidden')
    except ValueError as error:
        if 'Private' in str(error):
            raise
        if '.' not in host or host.endswith(('.localhost', '.local', '.internal')):
            raise ValueError('Public hostname required') from None
    return value


class DirectoryRecord(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    identifier: str = Field(min_length=3, max_length=120, pattern=r'^(AISHE|UGC|OFFICIAL):[A-Za-z0-9_.-]+$')
    name: str = Field(min_length=1, max_length=255)
    state: str = Field(min_length=1, max_length=100)
    district: str | None = Field(default=None, max_length=150)
    city: str | None = Field(default=None, max_length=150)
    category: str = Field(min_length=1, max_length=100)
    website: str | None = Field(default=None, max_length=500)
    website_evidence_url: str | None = Field(default=None, max_length=500)
    website_verified_at: datetime | None = None
    event_urls: list[str] = Field(default_factory=list, max_length=50)
    verified_at: datetime

    @field_validator('website', 'website_evidence_url')
    @classmethod
    def urls(cls, value):
        return public_https(value) if value else None

    @field_validator('verified_at', 'website_verified_at')
    @classmethod
    def dates(cls, value):
        if value is not None and (value.tzinfo is None or value > datetime.now(timezone.utc)):
            raise ValueError('Verification must be timezone-aware and not in the future')
        return value

    @model_validator(mode='after')
    def evidence(self):
        if self.website and not (self.website_evidence_url and self.website_verified_at):
            raise ValueError('Website requires official evidence and verification date')
        if self.event_urls and not self.website:
            raise ValueError('Verified event URLs require a verified website')
        if len(set(self.event_urls)) != len(self.event_urls):
            raise ValueError('Duplicate event URLs')
        for url in self.event_urls:
            public_https(url)
            if urlsplit(url).netloc != urlsplit(self.website).netloc or len(url) > 500:
                raise ValueError('Event URL must belong to the verified website origin')
        return self


class DirectoryImport(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    provider: Literal['aishe', 'ugc', 'institution']
    source_url: str = Field(max_length=500)
    reuse_permitted: StrictBool
    license_reference: str = Field(min_length=1, max_length=500)
    reviewed_by: str = Field(min_length=1, max_length=150)
    records: list[DirectoryRecord] = Field(min_length=1, max_length=5000)

    @model_validator(mode='after')
    def permission(self):
        public_https(self.source_url)
        host = urlsplit(self.source_url).hostname
        domains = {'aishe': ('aishe.gov.in', 'data.gov.in', 'aikosh.indiaai.gov.in'), 'ugc': ('ugc.gov.in', 'data.gov.in')}
        if self.provider in domains and not any(host == d or host.endswith('.' + d) for d in domains[self.provider]):
            raise ValueError('Official provider provenance required')
        if not self.reuse_permitted:
            raise ValueError('Directory reuse approval is required')
        identifiers = [row.identifier for row in self.records]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError('Duplicate institution identifier in batch')
        prefix = {'aishe': 'AISHE:', 'ugc': 'UGC:', 'institution': 'OFFICIAL:'}[self.provider]
        if any(not row.identifier.startswith(prefix) for row in self.records):
            raise ValueError('Institution identifier must match provider')
        return self

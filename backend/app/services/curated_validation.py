"""Shared database-free validation for the reviewed factual manifest."""
from urllib.parse import urlsplit
from app.schemas.event import EventCreate


def validate_records(payload):
    if not isinstance(payload, list) or not 1 <= len(payload) <= 100:
        raise ValueError('Expected 1–100 reviewed records')
    records = []
    for item in payload:
        event = EventCreate.model_validate(item)
        parts = urlsplit(str(event.url or ''))
        if (event.source != 'Official organizer (manual)' or not event.organization
                or event.organization_id is not None or parts.scheme != 'https'
                or parts.username or parts.password or not event.scraped_at
                or not event.description or 'Date precision:' not in event.description):
            raise ValueError('Reviewed provenance, HTTPS source and date precision required')
        records.append(event)
    return records

from datetime import datetime, timezone
from uuid import UUID, uuid4


def utc_now() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(timezone.utc)


def generate_request_id() -> str:
    """Generate a unique request/correlation ID."""
    return str(uuid4())


def is_valid_uuid(value: str) -> bool:
    """Return True when the provided string is a valid UUID."""
    try:
        UUID(value)
        return True
    except (ValueError, AttributeError, TypeError):
        return False
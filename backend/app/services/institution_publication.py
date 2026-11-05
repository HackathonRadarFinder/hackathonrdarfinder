"""Directory publication is separate from permission to collect event sources."""
from sqlalchemy import true
from app.models.institution import Institution
from app.schemas.institution import public_https


def public_institution_filters():
    """Fail closed for legacy, pending, or unreviewed directory records."""
    return (
        Institution.permission_status == 'approved',
        Institution.provenance['reuse_permitted'].as_boolean() == true(),
        Institution.provenance['directory_publication_approved'].as_boolean() == true(),
    )


def public_source_url(provenance):
    """Malformed/legacy provenance must neither crash nor leak private URLs."""
    value = provenance.get('source_url') if isinstance(provenance, dict) else None
    if not isinstance(value, str):
        return None
    try:
        return public_https(value)
    except (ValueError, TypeError):
        return None

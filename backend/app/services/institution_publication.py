"""Explicitly scoped institution directory publication rules.

The mined public listing is a copy of factual fields only. Publication
authorization by the portal owner is tracked separately from the original
dataset's unconfirmed third-party reuse permission. Original staging records
and their permission metadata are not changed.
"""
from sqlalchemy import and_, or_, true
from app.models.institution import Institution
from app.schemas.institution import public_https


def public_institution_filters():
    """Show separately approved directories or owner-published factual listings."""
    reviewed = and_(
        Institution.permission_status == 'approved',
        Institution.provenance['reuse_permitted'].as_boolean() == true(),
        Institution.provenance['directory_publication_approved'].as_boolean() == true(),
    )
    mined_factual_listing = and_(
        Institution.permission_status == 'awaiting_permission',
        Institution.provenance['collection_method'].as_string() == 'data_mined',
        Institution.provenance['publication_scope'].as_string() == 'factual_fields_only',
        Institution.provenance['owner_publication_authorized'].as_boolean() == true(),
    )
    return (or_(reviewed, mined_factual_listing),)


def public_source_url(provenance):
    """Malformed/legacy provenance must neither crash nor leak private URLs."""
    value = provenance.get('source_url') if isinstance(provenance, dict) else None
    if not isinstance(value, str):
        return None
    try:
        return public_https(value)
    except (ValueError, TypeError):
        return None

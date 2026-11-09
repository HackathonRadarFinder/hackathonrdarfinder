"""Conservative eligibility checks for unattended college event publication.

This module does not fetch URLs, infer crawling rights, or write to a database.
It can be called by the existing discovery ingestion path after source-policy
validation and authoritative database duplicate checks.
"""
from datetime import date
from urllib.parse import urlsplit


def _https_url(value):
    if not isinstance(value, str):
        return False
    try:
        parsed = urlsplit(value)
        return parsed.scheme == "https" and bool(parsed.hostname) and not parsed.username and not parsed.password
    except ValueError:
        return False


def publication_decision(candidate, *, source_permission_verified=False,
                         source_verified=False, duplicate_checked=False,
                         duplicate_found=False, institution_verified=False):
    """Return (eligible, reasons). Missing proof always blocks publication."""
    reasons = []
    if not source_permission_verified:
        reasons.append("source_permission_unverified")
    if not source_verified:
        reasons.append("official_source_unverified")
    if not duplicate_checked:
        reasons.append("database_duplicate_check_missing")
    elif duplicate_found:
        reasons.append("duplicate")
    if not institution_verified:
        reasons.append("institution_identity_unverified")
    if not candidate.get("title") or not candidate.get("hosting_college"):
        reasons.append("missing_identity")
    if not _https_url(candidate.get("official_source_url")):
        reasons.append("invalid_source_url")
    if not _https_url(candidate.get("registration_url")):
        reasons.append("registration_url_unverified")
    try:
        start = date.fromisoformat(candidate["start_date"])
        end = date.fromisoformat(candidate["end_date"])
        if end < start:
            reasons.append("invalid_date_range")
    except (ValueError, KeyError, TypeError):
        reasons.append("dates_unverified")
    if candidate.get("uncertainty"):
        reasons.append("unresolved_uncertainty")
    return not reasons, reasons

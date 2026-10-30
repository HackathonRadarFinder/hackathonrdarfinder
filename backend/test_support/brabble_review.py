"""Synthetic review attestations for disposable tests, explicitly refused by CLI apply."""
from copy import deepcopy
from app.schemas.event import EventCreate
from app.services.review_evidence import CHECK_FIELDS, event_digest


def test_attestation(event, date_precision='unknown'):
    return {'decision': 'approved', 'reviewer': 'Disposable test fixture', 'reviewer_type': 'test_fixture',
            'reviewed_at': '2026-10-25T17:00:00+00:00', 'event_sha256': event_digest(event),
            'date_precision': date_precision,
            'permission_review': {'basis_url': 'https://brabble.ai/docs',
                                  'note': 'Synthetic test permission attestation; not real review'},
            'unresolved_conflicts': [],
            'checks': {field: {'status': 'verified' if getattr(event, field) is not None else 'unknown',
                               'evidence_url': str(event.url),
                               'note': 'Synthetic assertion for a disposable test; no source verification claimed'}
                       for field in CHECK_FIELDS}}


def attest_row(row):
    from workers.import_reviewed_public import ACCEPT
    event = EventCreate.model_validate({key: row.get(key) or None for key in ACCEPT})
    row['acquisition_evidence']['review'] = test_attestation(event, row['date_precision'])


def attest_record(record):
    evidence = deepcopy(record.acquisition_evidence)
    evidence['review'] = test_attestation(record.event, record.date_precision)
    return record._replace(acquisition_evidence=evidence)

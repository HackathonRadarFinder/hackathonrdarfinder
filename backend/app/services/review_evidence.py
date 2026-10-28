"""Review attestations bind reviewed facts to a specific normalized event."""
import hashlib
import json
from datetime import datetime, timezone

from radar_collector.radar_scraper import clean_url

CHECK_FIELDS = ('title', 'organization', 'url', 'start_date', 'end_date',
                'registration_deadline', 'location', 'mode', 'prize')


def event_digest(event):
    values = event.model_dump(mode='json')
    # Optional India directory fields did not exist in the original review contract.
    # Preserve old attestations only when these facts remain absent; any supplied
    # value is hashed and therefore requires a fresh factual review.
    for field in ('state', 'institution_id', 'registration_url', 'eligibility'):
        if values.get(field) is None:
            values.pop(field, None)
    if values.get('url'):
        values['url'] = clean_url(values['url'])
    return hashlib.sha256(json.dumps(values, sort_keys=True, ensure_ascii=False,
                                    separators=(',', ':')).encode('utf-8')).hexdigest()


def review_timestamp(value):
    observed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    if observed.tzinfo is None:
        raise ValueError('Review timestamp requires a timezone')
    if observed > datetime.now(timezone.utc):
        raise ValueError('Review timestamp cannot be in the future')
    return observed


def validate_review(event, evidence, date_precision):
    review = evidence.get('review')
    if not isinstance(review, dict) or review.get('decision') != 'approved':
        raise ValueError('Complete per-record review metadata is required')
    if (not isinstance(review.get('reviewer'), str) or not review['reviewer'].strip()
            or len(review['reviewer']) > 100
            or review.get('reviewer_type') not in {'human', 'ai_assistant', 'test_fixture'}):
        raise ValueError('A truthful reviewer identity/type is required')
    review_timestamp(review.get('reviewed_at', ''))
    if review.get('event_sha256') != event_digest(event):
        raise ValueError('Reviewed facts changed; repeat factual review')
    if review.get('date_precision') != date_precision:
        raise ValueError('Reviewed date precision changed; repeat factual review')
    permission = review.get('permission_review', {})
    if permission.get('basis_url') != 'https://brabble.ai/docs' or not permission.get('note'):
        raise ValueError('Documented API reuse permission review is required')
    checks = review.get('checks', {})
    for field in CHECK_FIELDS:
        check = checks.get(field, {})
        present = getattr(event, field) is not None
        expected = 'verified' if present else 'unknown'
        if (check.get('status') != expected or not check.get('note')
                or not str(check.get('evidence_url', '')).startswith('https://')):
            raise ValueError(f'Incomplete or inconsistent factual review: {field}')
    if review.get('unresolved_conflicts'):
        raise ValueError('Unresolved factual conflicts prevent approval')
    return review


def require_human_approval(record):
    """An applying operator name is not evidence of a human approval.

    Keep AI factual review intact; a human can add a separate, value-bound
    approval. Disposable acceptance may exercise AI-reviewed records, but CLI
    application to the development catalog requires this gate.
    """
    evidence = record.acquisition_evidence
    if record.collection_mode != 'brabble_api':
        return  # Existing manually reviewed HTML contract is unchanged.
    review = validate_review(record.event, evidence, record.date_precision)
    if review['reviewer_type'] == 'human':
        return
    approval = evidence.get('human_approval', {})
    if (approval.get('reviewer_type') != 'human' or approval.get('decision') != 'approved'
            or not isinstance(approval.get('reviewer'), str) or not approval['reviewer'].strip()
            or len(approval['reviewer']) > 100 or not approval.get('note')):
        raise ValueError('Human approval is required; AI verification is not human approval')
    checked = review_timestamp(approval.get('approved_at', ''))
    if checked < review_timestamp(review['reviewed_at']):
        raise ValueError('Human approval cannot precede the factual review')
    if approval.get('event_sha256') != event_digest(record.event):
        raise ValueError('Human approval must be dated and bound to the reviewed facts')
    if approval.get('date_precision') != record.date_precision:
        raise ValueError('Human approval must cover date precision')

"""Build a non-importable AI review worksheet without changing evidence or approvals.

No network or database access. Observations are research notes, not attestations.
Generated datasets belong in the ignored collector output directory.
"""
import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from app.services.brabble_adapter import validate_evidence
from app.services.review_evidence import CHECK_FIELDS, review_timestamp
from radar_collector.radar_scraper import clean_url, csv_safe

STATUSES = {'unverified', 'verified', 'unknown', 'conflict', 'indexed_claim'}
REQUIRED = {'title', 'organization', 'url', 'start_date', 'end_date', 'location', 'mode'}


def build_packet(candidates, observations, output):
    original = candidates.read_bytes()
    notes_bytes = observations.read_bytes()
    notes = json.loads(notes_bytes.decode('utf-8-sig'))
    observed = review_timestamp(notes['observed_at'])
    with candidates.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError('Missing or duplicate candidate headers')
        rows = list(reader)
    ids, urls, records = set(), set(), []
    for row in rows:
        if None in row or None in row.values():
            raise ValueError('Malformed candidate column count')
        evidence = validate_evidence(json.loads(row['acquisition_evidence']))
        provider_id = evidence['provider_id']
        url = clean_url(row['url'])
        if provider_id in ids or url in urls:
            raise ValueError('Duplicate pilot identity or URL')
        ids.add(provider_id)
        urls.add(url)
        note = notes['records'][provider_id]  # Require an explicit observation per candidate.
        if set(note.get('fields', {})) - set(CHECK_FIELDS):
            raise ValueError('Unexpected review field')
        fields = {}
        for field in CHECK_FIELDS:
            check = dict(note.get('fields', {}).get(field, {}))
            status = check.setdefault('status', 'unverified')
            if status not in STATUSES:
                raise ValueError('Unknown factual status')
            if status in {'verified', 'indexed_claim', 'conflict'} and not (check.get('evidence_url', '').startswith('https://') and check.get('note')):
                raise ValueError('Factual findings require a public evidence URL and note')
            if status in {'unknown', 'unverified', 'conflict'} and check.get('value') is not None:
                raise ValueError('Unresolved fields cannot supply a corrected value')
            if status == 'verified' and check.get('value') in (None, ''):
                raise ValueError('Verified fields require a value')
            check['provider_claim'] = row.get(field) or None
            fields[field] = check
        verified = {key: check['value'] for key, check in fields.items() if check['status'] == 'verified'}
        for key in ('start_date', 'end_date', 'registration_deadline'):
            if verified.get(key):
                datetime.fromisoformat(verified[key].replace('Z', '+00:00'))
        if verified.get('start_date') and verified.get('end_date'):
            def utc(value):
                date = datetime.fromisoformat(value.replace('Z', '+00:00'))
                return date.replace(tzinfo=timezone.utc) if date.tzinfo is None else date.astimezone(timezone.utc)
            if utc(verified['end_date']) < utc(verified['start_date']):
                raise ValueError('Reversed proposed event chronology')
        ready = REQUIRED.issubset(verified) and not any(check['status'] == 'conflict' for check in fields.values())
        records.append({'provider_id': provider_id, 'title': row['title'], 'url': row['url'],
            'observed_at': observed.isoformat(), 'access': note['access'], 'fields': fields,
            'acquisition_evidence': evidence, 'permission_reference': row['permission_reference'],
            'priority_deadline_claim': row.get('registration_deadline') or '',
            'disposition': 'awaiting_human_approval' if ready else 'blocked_factual_review',
            'blockers': note.get('blockers', []), 'human_approved': False})
    if ids != set(notes['records']):
        raise ValueError('Observations must match the complete pilot')
    records.sort(key=lambda r: (not bool(r['priority_deadline_claim']), r['priority_deadline_claim'], r['title']))
    # Keep output separate even if a caller accidentally passes a source directory.
    output = output.resolve()
    targets = [output / name for name in ('field_review.json', 'corrected_worksheet.csv', 'awaiting_human_approval.csv', 'blocked_candidates.csv', 'FACTUAL_REVIEW.md', 'manifest.json')]
    if candidates.resolve() in targets or observations.resolve() in targets:
        raise ValueError('Review output cannot overwrite input evidence')
    output.mkdir(parents=True, exist_ok=True)
    (output / 'field_review.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
    columns = ['provider_id', 'candidate_title', 'original_url', 'field', 'provider_claim', 'proposed_value', 'status', 'evidence_url', 'note', 'observed_at', 'human_approved']
    with (output / 'corrected_worksheet.csv').open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for record in records:
            for field, check in record['fields'].items():
                values = dict(provider_id=record['provider_id'], candidate_title=record['title'], original_url=record['url'], field=field,
                    provider_claim=check['provider_claim'], proposed_value=check.get('value') if check['status'] == 'verified' else '',
                    status=check['status'], evidence_url=check.get('evidence_url', ''), note=check.get('note', ''), observed_at=record['observed_at'], human_approved='NO')
                writer.writerow({key: csv_safe(value if value is not None else '') for key, value in values.items()})
    for filename, status in [('awaiting_human_approval.csv', 'awaiting_human_approval'), ('blocked_candidates.csv', 'blocked_factual_review')]:
        with (output / filename).open('w', encoding='utf-8-sig', newline='') as handle:
            writer = csv.writer(handle)
            writer.writerow(['provider_id', 'candidate_title', 'original_url', 'blockers', 'human_approved'])
            for record in records:
                if record['disposition'] == status:
                    writer.writerow([csv_safe(record['provider_id']), csv_safe(record['title']), record['url'], csv_safe('; '.join(record['blockers'])), 'NO'])
    report = ['# Field-level factual review', '', 'AI research only. No human approval, database staging or publication. Priority uses provider deadline claims, not confirmed availability.', '',
        f"Observed: {observed.isoformat()}. Research extracts may be cached; relative countdowns were not interpreted as dates.", '']
    for record in records:
        report += [f"## {record['title']}", '', f"Original: {record['url']}", f"Disposition: {record['disposition']}; access: {record['access']}", '', '| Field | Claim | Proposed value | Status | Evidence / note |', '|---|---|---|---|---|']
        for field, check in record['fields'].items():
            cells = [field, check['provider_claim'], check.get('value'), check['status'], f"{check.get('evidence_url', '')} {check.get('note', '')}"]
            report.append('| ' + ' | '.join(str(cell or '').replace('|', '/').replace('\n', ' ') for cell in cells) + ' |')
        report += ['', 'Blockers: ' + '; '.join(record['blockers']), '']
    (output / 'FACTUAL_REVIEW.md').write_text('\n'.join(report), encoding='utf-8')
    result = {'candidate_count': len(records), 'field_count': len(records) * len(CHECK_FIELDS),
        'awaiting_human_approval': sum(r['disposition'] == 'awaiting_human_approval' for r in records),
        'human_approved': 0, 'published': 0, 'database_connected': False,
        'candidate_sha256': hashlib.sha256(original).hexdigest(), 'observations_sha256': hashlib.sha256(notes_bytes).hexdigest(),
        'observed_at': observed.isoformat()}
    (output / 'manifest.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidates', type=Path, required=True)
    parser.add_argument('--observations', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build_packet(args.candidates, args.observations, args.out), indent=2))


if __name__ == '__main__':
    main()

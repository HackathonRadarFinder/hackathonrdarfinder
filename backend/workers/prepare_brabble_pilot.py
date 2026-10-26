"""Offline pilot selection and application of explicit, evidence-backed review decisions."""
import argparse
import copy
import csv
import json
from pathlib import Path

from app.schemas.event import EventCreate
from app.services.review_evidence import CHECK_FIELDS, event_digest
from radar_collector.radar_scraper import FIELDS, csv_safe
from workers.import_reviewed_public import ACCEPT, ReviewedRecord, validate_approved


def write_csv(path, rows):
    with path.open('w', encoding='utf-8-sig', newline='') as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            values = dict(row, acquisition_evidence=json.dumps(row['acquisition_evidence'], ensure_ascii=False))
            writer.writerow({key: csv_safe(values.get(key, '')) for key in FIELDS})


def prepare_pilot(queue, decisions, output):
    rows = json.loads(queue.read_text(encoding='utf-8-sig'))
    ledger = json.loads(decisions.read_text(encoding='utf-8-sig'))
    # This is ranking, never approval. Favor complete, readable records with
    # deadlines after the acceptance target; the Devfolio row has a separate
    # original-page organizer correction in the explicit review ledger.
    ranked = [r for r in rows if r['organization'] and r['location'] and r['prize']
              and r['registration_deadline'] >= '2026-10-28'
              and not any(ord(ch) < 32 or 127 <= ord(ch) <= 159 or ch == '\ufffd' for ch in r['title'])]
    selected = copy.deepcopy(ranked[:24])
    special_id = ledger['additional_candidate_id']
    additional = next(r for r in rows if r['acquisition_evidence']['provider_id'] == special_id)
    if additional['url'] not in {r['url'] for r in selected}:
        selected.append(copy.deepcopy(additional))
    if not 20 <= len(selected) <= 30:
        raise ValueError('Pilot selection requires 20 to 30 distinct candidates')
    approved, checklists = [], []
    for row in selected:
        provider_id = row['acquisition_evidence']['provider_id']
        decision = ledger.get('decisions', {}).get(provider_id, {})
        observation = ledger.get('access_observations', {}).get(provider_id, {
            'status': 'not_individually_checked',
            'note': 'Repeated unreadable Unstop responses in this session; no alternate/private API or bypass attempted.'})
        checks = {field: {'status': 'unverified', 'verified_value': None,
                          'provider_claim': row.get(field) or None} for field in CHECK_FIELDS}
        if decision.get('decision') == 'approved':
            overrides = decision.get('verified_values', {})
            if set(overrides) - set(ACCEPT):
                raise ValueError('Unexpected event-field override')
            row.update(overrides)
            event = EventCreate.model_validate({key: row.get(key) or None for key in ACCEPT})
            review = copy.deepcopy(decision['review'])
            review['event_sha256'] = event_digest(event)
            review['date_precision'] = decision['date_precision']
            row['acquisition_evidence']['verified_fields'] = ['organization', 'url', 'dates']
            row['acquisition_evidence']['review'] = review
            row['review_status'] = 'approved'
            row['date_precision'] = decision['date_precision']
            row['issues'] = decision.get('remaining_unknowns', '')
            validate_approved(ReviewedRecord(event, '', row['date_precision'], 'brabble_api',
                                            row['permission_reference'], row['acquisition_evidence']))
            approved.append(row)
            for field in CHECK_FIELDS:
                checks[field] = dict(review['checks'][field], verified_value=row.get(field) or None)
        else:
            # A supplied pending/conflict decision cannot become an approval.
            row['review_status'] = 'needs_review'
            row['acquisition_evidence']['verified_fields'] = []
            checks.update(decision.get('checks', {}))
        checklists.append({'provider_id': provider_id, 'title': row['title'], 'original_url': row['url'],
                           'decision': row['review_status'], 'access': observation, 'checks': checks,
                           'blockers': decision.get('blockers', ['Original-page organizer, URL and date review incomplete'])
                           if row['review_status'] != 'approved' else [],
                           'reviewer': decision.get('review', {}).get('reviewer'),
                           'reviewed_at': decision.get('review', {}).get('reviewed_at')})
    output.mkdir(parents=True, exist_ok=True)
    (output / 'selection.json').write_text(json.dumps([
        {'provider_id': row['acquisition_evidence']['provider_id'], 'title': row['title'],
         'url': row['url'], 'source': row['source']} for row in selected],
        ensure_ascii=False, indent=2), encoding='utf-8')
    write_csv(output / 'pilot_candidates.csv', selected)
    write_csv(output / 'reviewed.csv', approved)
    (output / 'evidence_checklist.json').write_text(json.dumps(checklists, ensure_ascii=False, indent=2), encoding='utf-8')
    text = ['# Pilot factual review', '',
            f'Selected {len(selected)} candidates; explicitly reviewed/approved {len(approved)}; pending {len(selected)-len(approved)}.',
            'Review was performed by Codex as an AI assistant at the user’s explicit request; no human identity is asserted.',
            'Provider claims are not verification. Unknown facts remain null in the checklist and blank in approved CSV.', '']
    for item in checklists:
        text += [f"## {item['title']}", '', f"Original page: {item['original_url']}",
                 f"Decision: {item['decision']}; access: {item['access']['status']}",
                 '| Field | Status | Verified value |', '|---|---|---|']
        for field, check in item['checks'].items():
            text.append(f"| {field} | {check['status']} | {check.get('verified_value') or 'unknown'} |")
        text += ['', 'Blockers: ' + '; '.join(item['blockers']), '']
    (output / 'evidence_checklist.md').write_text('\n'.join(text), encoding='utf-8')
    return {'selected': len(selected), 'approved': len(approved), 'pending': len(selected)-len(approved),
            'automatic_approvals': False, 'database_writes': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--queue', type=Path, default=Path('radar_collector/output/brabble-review/review_queue.json'))
    parser.add_argument('--decisions', type=Path, default=Path('radar_collector/output/brabble-pilot/review_decisions.json'))
    parser.add_argument('--out', type=Path, default=Path('radar_collector/output/brabble-pilot'))
    args = parser.parse_args()
    print(json.dumps(prepare_pilot(args.queue, args.decisions, args.out)))


if __name__ == '__main__':
    main()

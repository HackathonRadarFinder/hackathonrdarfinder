"""Offline research evaluation: fixed reviewed manifest or existing discovery export."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from ai.temporal_prediction import evaluate, load_review, offline_observations, historical_observations, timestamp


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', help='Version-1 discovery export or verified historical dataset; default: reviewed offline snapshot')
    parser.add_argument('--output', required=True, help='New research artifact; never overwrite existing files')
    parser.add_argument('--as-of', help='Evaluation ceiling; default: current UTC')
    parser.add_argument('--cutoff', action='append', help='Forecast cutoffs; default: 90 days before each historical target')
    parser.add_argument('--neural', action='store_true', help='Research refits only after 30 earlier available labels; never writes model artifacts')
    parser.add_argument('--actual-outcomes', help='Reviewed JSON actual-occurrence labels; absent by default')
    args = parser.parse_args()
    now = timestamp(args.as_of) if args.as_of else datetime.now(timezone.utc).replace(tzinfo=None)
    if now > datetime.now(timezone.utc).replace(tzinfo=None):
        parser.error('Evaluation cannot claim future evidence')
    if args.input:
        export = json.loads(Path(args.input).read_text(encoding='utf-8'))
        if export.get('schema_version') != 1:
            parser.error('Expected a version-1 discovery observations export')
        if isinstance(export.get('historical_editions'), list):
            observations = historical_observations(export)
        elif isinstance(export.get('observations'), list):
            observations = export['observations']
        else:
            parser.error('Expected discovery observations or verified historical editions')
    else:
        observations = offline_observations()
    review, checksum = load_review()
    outcomes = json.loads(Path(args.actual_outcomes).read_text(encoding='utf-8')) if args.actual_outcomes else []
    if not isinstance(outcomes, list):
        parser.error('Actual outcomes must be a reviewed JSON list')
    report = evaluate(observations, review, now, args.cutoff, neural=args.neural, actual_outcomes=outcomes)
    artifact = {'review_checksum': checksum, 'observations': observations, 'evaluation': report}
    with Path(args.output).open('x', encoding='utf-8') as output:
        json.dump(artifact, output, indent=2)
    print(json.dumps({'status': report['status'], 'dataset': report['dataset'], 'metrics': report['metrics']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

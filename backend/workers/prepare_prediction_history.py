"""Read-only export of discovery observations and optional temporal baseline evaluation."""
import argparse
from datetime import datetime
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, help='New JSON artifact; existing files are never overwritten')
    parser.add_argument('--families', help='Reviewed JSON mapping of event ID strings to recurrence family IDs')
    parser.add_argument('--cutoff', action='append', default=[], help='UTC-naive ISO cutoff; repeat for temporal folds')
    parser.add_argument('--evaluation-as-of', required=True, help='UTC-naive ISO label observation ceiling')
    args = parser.parse_args()
    from app.core.database import SessionLocal
    from ai.discovery_history import export_observations, backtest
    evaluation = datetime.fromisoformat(args.evaluation_as_of)
    cutoffs = [datetime.fromisoformat(value) for value in args.cutoff]
    if evaluation.tzinfo or any(value.tzinfo for value in cutoffs):
        parser.error('Use UTC-naive ISO timestamps matching stored evidence')
    families = json.loads(Path(args.families).read_text()) if args.families else {}
    if not isinstance(families, dict) or any(not isinstance(key, str) or not isinstance(value, str) or not value.strip() for key, value in families.items()):
        parser.error('Family map must contain nonblank string identifiers')
    with SessionLocal() as db:
        observations = [row for row in export_observations(db)
            if datetime.fromisoformat(row['observed_at']) <= evaluation]
        db.rollback()
    artifact = {'schema_version': 1, 'evaluation_as_of': evaluation.isoformat(),
        'observations': observations, 'evaluation': backtest(observations, families, cutoffs, evaluation)}
    with Path(args.output).open('x', encoding='utf-8') as output:
        json.dump(artifact, output, indent=2)
    print(json.dumps({'observations': len(observations), **artifact['evaluation']}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

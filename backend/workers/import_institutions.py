"""Import an approved local JSON export or mapped AISHE/UGC CSV; never fetches URLs."""
import argparse
import csv
import json
from pathlib import Path
from app.schemas.institution import DirectoryImport


def load_export(path, metadata=None, columns=None, verified_at=None):
    path = Path(path)
    if path.stat().st_size > 10_000_000:
        raise ValueError('Directory batch exceeds 10 MB; split into incremental batches')
    if path.suffix.lower() != '.csv':
        return DirectoryImport.model_validate(json.loads(path.read_text(encoding='utf-8-sig')))
    if metadata is None or columns is None:
        raise ValueError('CSV requires approved metadata and an explicit source-column map')
    # Explicit mapping prevents guessing which administrative field means district/city.
    records = []
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if not set(columns.values()).issubset(reader.fieldnames or []):
            raise ValueError('Mapped column is missing')
        for row in reader:
            if len(records) >= 5000:
                raise ValueError('Maximum batch is 5000 institutions')
            item = {field: row[column] or None for field, column in columns.items()}
            if verified_at and not item.get('verified_at'):
                item['verified_at'] = verified_at
            if item.get('identifier') and ':' not in item['identifier']:
                item['identifier'] = {'aishe': 'AISHE:', 'ugc': 'UGC:', 'institution': 'OFFICIAL:'}[metadata['provider']] + item['identifier']
            # URLs/verification are not assumed from an unverified website column.
            records.append(item)
    return DirectoryImport.model_validate({**metadata, 'records': records})


def _batch_paths(args):
    if args.input_dir:
        paths = sorted(Path(args.input_dir).glob('*.csv'))
        if not paths:
            raise ValueError('No CSV batches found in --input-dir')
        return paths
    return [Path(args.input)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--input', help='One JSON export or CSV batch')
    source.add_argument('--input-dir', help='Folder of CSV batches (each at most 5000 rows), imported in file-name order')
    parser.add_argument('--metadata', help='JSON permission/provenance envelope for CSV')
    parser.add_argument('--columns', help='JSON map from canonical field to CSV column')
    parser.add_argument('--verified-at', help='Timezone-aware operator verification timestamp for CSV rows without one')
    parser.add_argument('--validate-only', action='store_true')
    parser.add_argument('--expect-total', type=int, help='Fail unless exactly this many distinct institutions were processed and are present afterwards')
    args = parser.parse_args()
    read = lambda path: json.loads(Path(path).read_text(encoding='utf-8')) if path else None
    metadata, columns = read(args.metadata), read(args.columns)
    paths = _batch_paths(args)
    if len(paths) == 1 and not args.input_dir and not args.expect_total:
        # Original single-file behaviour and output are unchanged.
        export = load_export(paths[0], metadata, columns, args.verified_at)
        if args.validate_only:
            print(json.dumps(dict(validated=len(export.records), database_written=False)))
            return 0
        from app.core.database import SessionLocal
        from app.services.institution_service import import_directory
        with SessionLocal() as db:
            try:
                result = import_directory(db, export)
                db.commit()
            except Exception:
                db.rollback()
                raise
        print(json.dumps(result))
        return 0

    # Batch mode: every file is validated first, then imported in its own transaction. Re-running is safe because
    # unchanged rows are skipped, so a failed run can simply be started again.
    exports = [(path, load_export(path, metadata, columns, args.verified_at)) for path in paths]
    identifiers = [record.identifier for _, export in exports for record in export.records]
    report = dict(batches=len(exports), validated=len(identifiers), distinct_identifiers=len(set(identifiers)),
                  database_written=False)
    verified = args.expect_total is None or report['distinct_identifiers'] == args.expect_total
    if not args.validate_only and verified:
        from sqlalchemy import func, select
        from app.core.database import SessionLocal
        from app.models.institution import Institution
        from app.services.institution_service import import_directory
        totals = dict(inserted=0, updated=0, unchanged=0, stale=0)
        for path, export in exports:
            with SessionLocal() as db:
                try:
                    counts = import_directory(db, export)
                    db.commit()
                except Exception as error:
                    db.rollback()
                    raise SystemExit(f'Batch {path.name} failed and was rolled back: {error}')
                for key, value in counts.items():
                    totals[key] += value
        distinct = sorted(set(identifiers))
        present = 0
        with SessionLocal() as db:  # counted in chunks so no query binds more than 5000 values
            for start in range(0, len(distinct), 5000):
                present += db.scalar(select(func.count()).select_from(Institution).where(
                    Institution.identifier.in_(distinct[start:start + 5000])))
        report.update(totals, database_written=True, present_in_database=present)
        verified = args.expect_total is None or present == args.expect_total
    if args.expect_total is not None:
        report.update(expected_total=args.expect_total, verified=verified)
    print(json.dumps(report))
    return 0 if verified else 1


if __name__ == '__main__':
    raise SystemExit(main())

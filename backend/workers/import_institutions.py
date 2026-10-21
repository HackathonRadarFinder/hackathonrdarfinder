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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--metadata', help='JSON permission/provenance envelope for CSV')
    parser.add_argument('--columns', help='JSON map from canonical field to CSV column')
    parser.add_argument('--verified-at', help='Timezone-aware operator verification timestamp for CSV rows without one')
    parser.add_argument('--validate-only', action='store_true')
    args = parser.parse_args()
    read = lambda path: json.loads(Path(path).read_text(encoding='utf-8')) if path else None
    export = load_export(args.input, read(args.metadata), read(args.columns), args.verified_at)
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


if __name__ == '__main__':
    raise SystemExit(main())

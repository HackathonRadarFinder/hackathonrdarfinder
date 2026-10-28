"""Bounded offline dataset ingestion into the existing human review queue."""
import base64
import binascii
import csv
import hashlib
import io
import json
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import PurePath
from fastapi import HTTPException
from pydantic import ValidationError, HttpUrl
from sqlalchemy import select
from app.models.core import AuditLog
from app.models.discovery import DiscoverySource
from app.schemas.discovery import SourcePolicy
from app.schemas.institution import public_https
from app.services.database import database_operation
from app.services.discovery_service import policy_reason
from app.services.nationwide_collection import stage_announcements

MAX_BYTES = 2_000_000
MAX_ROWS = 1000
FIELDS = {'title', 'organization', 'url', 'registration_url', 'start_date', 'end_date',
    'registration_deadline', 'description', 'eligibility', 'location', 'mode', 'prize', 'state'}
DATES = {'start_date', 'end_date', 'registration_deadline'}
LIMITS = {'title': 255, 'organization': 255, 'url': 500, 'registration_url': 500,
    'description': 5000, 'eligibility': 5000, 'location': 255, 'mode': 50, 'prize': 255, 'state': 100}


def invalid(message):
    raise HTTPException(422, message)


def read_table(filename, content):
    try:
        raw = base64.b64decode(content, validate=True)
    except (ValueError, binascii.Error):
        invalid('File content must use valid base64')
    if not raw or len(raw) > MAX_BYTES:
        invalid('Upload must contain at most 2 MB')
    suffix = PurePath(filename).suffix.lower()
    if suffix == '.csv':
        try:
            text = raw.decode('utf-8-sig')
            table = []
            for row in csv.reader(io.StringIO(text), strict=True):
                if len(table) > MAX_ROWS:
                    invalid('Dataset exceeds 1000 data rows')
                table.append(row)
        except (UnicodeError, csv.Error):
            invalid('CSV must be valid UTF-8 with a consistent comma-separated table')
        return raw, table
    if suffix != '.xlsx':
        invalid('Only CSV and XLSX files are supported')
    try:
        # Inspect ZIP expansion before handing it to the spreadsheet parser.
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            entries = archive.infolist()
            if len(entries) > 1000 or sum(item.file_size for item in entries) > 16_000_000:
                invalid('Workbook expanded size exceeds the upload limit')
        from openpyxl import load_workbook
        book = load_workbook(io.BytesIO(raw), read_only=True, data_only=False, keep_links=False)
        try:
            if len(book.worksheets) != 1:
                invalid('Workbook must contain exactly one worksheet')
            sheet = book.worksheets[0]
            if (sheet.max_row or 0) > MAX_ROWS + 1 or (sheet.max_column or 0) > len(FIELDS):
                invalid('Workbook exceeds the 1000-row or supported-column limit')
            table = []
            for cells in sheet.iter_rows():
                if len(table) > MAX_ROWS:
                    invalid('Dataset exceeds 1000 data rows')
                if any(cell.data_type == 'f' for cell in cells):
                    invalid('Formula cells are not accepted; upload explicit values')
                table.append([cell.value for cell in cells])
            return raw, table
        finally:
            book.close()
    except HTTPException:
        raise
    except Exception:
        invalid('Workbook could not be read as a supported XLSX table')


def parse_rows(table):
    if not table or len(table) < 2 or len(table) > MAX_ROWS + 1:
        invalid('Dataset must contain headers and 1 to 1000 data rows')
    headers = table[0]
    if any(not isinstance(value, str) for value in headers):
        invalid('Headers must be text field names')
    headers = [value.strip() for value in headers]
    if (len(set(headers)) != len(headers) or not {'title', 'url'}.issubset(headers)
            or not set(headers).issubset(FIELDS)):
        invalid('Use unique supported headers, including title and url')
    rows = []
    for index, cells in enumerate(table[1:], start=2):
        if len(cells) != len(headers):
            invalid(f'Row {index} does not match the header column count')
        if all(value is None or value == '' for value in cells):
            continue
        item, issues, raw_dates = {}, [], {}
        for field, value in zip(headers, cells):
            if value is None or value == '':
                continue
            if field in DATES:
                value = value.isoformat() if isinstance(value, datetime) else str(value).strip()
                if len(value) > 100:
                    invalid(f'Row {index} has an oversized date value')
                raw_dates[field] = value
                try:
                    parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    if parsed.tzinfo is None:
                        raise ValueError('timezone required')
                    item[field] = parsed.isoformat()
                except ValueError:
                    issues.append(f'{field}_requires_verified_timezone_or_date')
                continue
            if not isinstance(value, str):
                invalid(f'Row {index}: {field} must be text')
            value = value.strip()
            if len(value) > LIMITS[field] or any(ord(char) < 32 and char not in '\n\r\t' for char in value):
                invalid(f'Row {index}: {field} exceeds supported text bounds')
            if field in {'url', 'registration_url'}:
                try:
                    public_https(value)
                    value = str(HttpUrl(value))
                    public_https(value)
                    if len(value) > LIMITS[field]:
                        raise ValueError('Normalized URL exceeds supported bounds')
                except (ValueError, ValidationError):
                    invalid(f'Row {index}: source and registration links must be public HTTPS URLs')
            item[field] = value
        if not item.get('title') or not item.get('url'):
            invalid(f'Row {index} requires a title and source URL')
        if not item.get('start_date'):
            issues.append('start_date_requires_review')
        if not item.get('organization'):
            issues.append('organization_requires_review')
        if item.get('start_date') and item.get('end_date'):
            if datetime.fromisoformat(item['end_date']) < datetime.fromisoformat(item['start_date']):
                raw_dates['end_date'] = item.pop('end_date')
                issues.append('end_date_precedes_start_date')
        rows.append({**item, '_issues': issues, '_raw_dates': raw_dates})
    if not rows:
        invalid('Dataset contains no nonempty data rows')
    return rows


def import_dataset(db, body, actor):
    now = datetime.now(timezone.utc)
    with database_operation(db):
        source = db.scalar(select(DiscoverySource).where(DiscoverySource.key == body.source_key).with_for_update())
        if source is None:
            raise HTTPException(404, 'Register and approve the dataset source before uploading')
        try:
            policy = SourcePolicy.model_validate(source.config)
        except ValidationError:
            raise HTTPException(409, 'Source approval record is invalid') from None
        if (not source.enabled or not policy.terms_permit or policy_reason(policy, now, True)
                or body.approval_reference != policy.reference):
            raise HTTPException(409, 'A current enabled source with explicit reuse permission and matching approval reference is required')
        raw, table = read_table(body.filename, body.content_base64)
        rows = parse_rows(table)
        checksum = hashlib.sha256(raw).hexdigest()
        counts = stage_announcements(db, source, rows, dict(checksum=checksum,
            document_url=policy.url, adapter_version=policy.adapter, fetched_at=now.isoformat()), now.replace(tzinfo=None))
        db.add(AuditLog(user_id=uuid.UUID(actor.sub), action='dataset_import_staged',
            entity_type='source', entity_id=source.source_id, details=json.dumps({
                'filename': body.filename, 'checksum': checksum, 'approval_reference': policy.reference,
                'approval_basis': policy.basis, 'rows': len(rows), **counts})))
        db.commit()
        return {**counts, 'rows': len(rows), 'checksum': checksum, 'published': False,
            'message': 'Dataset staged for human review; no events published'}

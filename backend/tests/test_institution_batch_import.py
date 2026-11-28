"""INT-01: batch import of AISHE colleges is idempotent, verifies the total and keeps legacy checksums."""
import csv
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

BACKEND = Path(__file__).resolve().parents[1]
COLUMNS = {'identifier': 'id', 'name': 'name', 'state': 'state', 'district': 'district', 'city': 'city',
           'category': 'type', 'university': 'univ'}
METADATA = {'provider': 'aishe', 'source_url': 'https://aishe.gov.in/aishe-gis/', 'reuse_permitted': True,
            'license_reference': 'test licence reference', 'reviewed_by': 'tester'}
VERIFIED_AT = '2026-11-20T00:00:00+00:00'


def run(module_args, url):
    env = {**os.environ, 'DATABASE_URL': url, 'SECRET_KEY': 'test-only-migration-secret-123456789', 'EMAIL_MODE': 'disabled'}
    return subprocess.run([sys.executable, *module_args], cwd=BACKEND, env=env, capture_output=True, text=True)


@pytest.fixture
def workspace(tmp_path):
    url = f"sqlite:///{(tmp_path / 'import.db').as_posix()}"
    assert run(['-m', 'alembic', 'upgrade', 'head'], url).returncode == 0
    (tmp_path / 'metadata.json').write_text(json.dumps(METADATA))
    (tmp_path / 'columns.json').write_text(json.dumps(COLUMNS))
    (tmp_path / 'batches').mkdir()
    return tmp_path, url


def write_batch(folder, name, numbers, university=lambda n: f'University {n % 3}'):
    with (folder / 'batches' / name).open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(['id', 'name', 'state', 'district', 'city', 'type', 'univ'])
        for n in numbers:
            writer.writerow([f'C-{n:05d}', f'College {n}', 'Karnataka' if n % 2 else 'Kerala', f'District {n % 7}', f'City {n}',
                             'Engineering', university(n)])


def importer(workspace, *extra, columns='columns.json'):
    folder, url = workspace
    args = ['-m', 'workers.import_institutions', '--input-dir', str(folder / 'batches'), '--metadata', str(folder / 'metadata.json'),
            '--columns', str(folder / columns), '--verified-at', VERIFIED_AT, *extra]
    return run(args, url)


def scalar(url, sql):
    engine = create_engine(url)
    with engine.connect() as c:
        value = c.execute(text(sql)).scalar()
    engine.dispose()
    return value


def make_three_batches(folder):
    write_batch(folder, '01.csv', range(1, 41))
    write_batch(folder, '02.csv', range(41, 81))
    write_batch(folder, '03.csv', [*range(81, 101), 5])  # id 5 repeats an earlier row: it counts once


def test_validate_only_counts_distinct_colleges_and_writes_nothing(workspace):
    make_three_batches(workspace[0])
    ok = importer(workspace, '--validate-only', '--expect-total', '100')
    assert ok.returncode == 0, ok.stderr
    report = json.loads(ok.stdout)
    assert (report['batches'], report['validated'], report['distinct_identifiers'], report['database_written'], report['verified']) == (3, 101, 100, False, True)
    assert scalar(workspace[1], 'SELECT count(*) FROM institutions') == 0
    wrong = importer(workspace, '--validate-only', '--expect-total', '101')
    assert wrong.returncode == 1 and json.loads(wrong.stdout)['verified'] is False


def test_import_is_idempotent_and_verifies_the_total(workspace):
    folder, url = workspace
    make_three_batches(folder)
    first = importer(workspace, '--expect-total', '100')
    assert first.returncode == 0, first.stderr
    report = json.loads(first.stdout)
    assert (report['inserted'], report['unchanged'], report['present_in_database'], report['verified']) == (100, 1, 100, True)
    assert scalar(url, 'SELECT count(*) FROM institutions') == 100
    again = json.loads(importer(workspace, '--expect-total', '100').stdout)
    assert (again['inserted'], again['updated'], again['unchanged'], again['verified']) == (0, 0, 101, True)  # nothing duplicated or changed
    assert scalar(url, 'SELECT count(*) FROM institutions') == 100


def test_state_district_and_university_are_stored(workspace):
    folder, url = workspace
    write_batch(folder, '01.csv', [1])
    assert importer(workspace).returncode == 0
    engine = create_engine(url)
    with engine.connect() as c:
        row = c.execute(text("SELECT state, district, university, category FROM institutions WHERE identifier='AISHE:C-00001'")).one()
    engine.dispose()
    assert tuple(row) == ('Karnataka', 'District 1', 'University 1', 'Engineering')


def test_a_batch_without_university_keeps_the_legacy_checksum(workspace):
    folder, url = workspace
    (folder / 'legacy_columns.json').write_text(json.dumps({k: v for k, v in COLUMNS.items() if k != 'university'}))
    write_batch(folder, '01.csv', [1])
    assert importer(workspace, columns='legacy_columns.json').returncode == 0
    provenance = json.loads(scalar(url, "SELECT provenance FROM institutions WHERE identifier='AISHE:C-00001'"))
    legacy_values = {'identifier': 'AISHE:C-00001', 'name': 'College 1', 'state': 'Karnataka', 'district': 'District 1', 'city': 'City 1',
                     'category': 'Engineering', 'website': None, 'website_evidence_url': None, 'website_verified_at': None,
                     'event_urls': [], 'verified_at': VERIFIED_AT.replace('+00:00', 'Z')}
    # Same checksum the importer produced before the university field existed, so approved rows are not reset on re-import.
    assert provenance['checksum'] == hashlib.sha256(json.dumps(legacy_values, sort_keys=True).encode()).hexdigest()
    again = json.loads(importer(workspace, '--expect-total', '1', columns='legacy_columns.json').stdout)
    assert again['unchanged'] == 1 and again['updated'] == 0


def test_oversized_or_invalid_batches_are_rejected_before_any_write(workspace):
    folder, url = workspace
    write_batch(folder, '01.csv', range(1, 11))
    write_batch(folder, '02.csv', range(1, 5002))  # one row over the 5000 limit
    result = importer(workspace)
    assert result.returncode != 0 and 'Maximum batch is 5000' in result.stderr
    assert scalar(url, 'SELECT count(*) FROM institutions') == 0  # the valid first batch was not imported either

"""DEVOPS-007 aliases: real shell safety logic, mocked database commands only."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
BASH = Path('C:/Program Files/Git/bin/bash.exe')
if not BASH.exists():
    BASH = shutil.which('bash')
pytestmark = pytest.mark.skipif(not BASH, reason='Bash unavailable')


@pytest.fixture
def alias(tmp_path):
    archive = tmp_path / 'trusted.dump'
    archive.write_text('synthetic archive')
    log = tmp_path / 'calls.log'
    mocks = tmp_path / 'mocks.sh'
    mocks.write_text('''
pg_dump() {
  printf 'dump %s %s %s\\n' "$PGHOST" "$PGPORT" "$PGDATABASE" >> "$MOCK_LOG"
  (( ${MOCK_DUMP_STATUS:-0} == 0 )) || return 1
  while (( $# )); do
    if [[ "$1" == -f ]]; then printf 'archive' > "$2"; return 0; fi
    shift
  done
}
pg_restore() {
  printf 'restore %s\\n' "$*" >> "$MOCK_LOG"
  [[ "$1" == --list ]] && return 0
  return "${MOCK_RESTORE_STATUS:-0}"
}
createdb() { printf 'create %s\\n' "$*" >> "$MOCK_LOG"; return "${MOCK_CREATE_STATUS:-0}"; }
''', newline='\n')
    env = {key: value for key, value in os.environ.items() if not key.startswith(('PG', 'DB_', 'RESTORE_', 'TARGET_'))}
    env.update(BASH_ENV=mocks.as_posix(), MOCK_LOG=log.as_posix(), DB_HOST='isolated.invalid',
               DB_USER='test', DB_PORT='5433', DB_NAME='radar_test', BACKUP_DIR=(tmp_path / 'backups').as_posix())
    def run(script, *args, **changes):
        result = subprocess.run([str(BASH), str(ROOT / 'scripts' / script), *args], cwd=tmp_path,
            env={**env, **changes}, capture_output=True, text=True, timeout=10)
        return result, log.read_text() if log.exists() else ''
    return run, archive, tmp_path


def test_backup_alias_maps_legacy_environment_from_another_directory(alias):
    run, _, folder = alias
    result, log = run('backup-database.sh')
    assert result.returncode == 0, result.stderr
    assert 'dump isolated.invalid 5433 radar_test' in log
    assert 'restore --list' in log
    assert len(list((folder / 'backups').glob('*.dump'))) == 1


def test_failed_dump_publishes_nothing_and_preserves_prior_backups(alias):
    run, _, folder = alias
    (folder / 'backups').mkdir()
    old = folder / 'backups' / 'prior.dump'
    old.write_text('keep this backup')
    result, _ = run('backup-database.sh', MOCK_DUMP_STATUS='1')
    assert result.returncode != 0
    assert list((folder / 'backups').iterdir()) == [old]


def test_restore_requires_explicit_target_and_confirmation(alias):
    run, archive, _ = alias
    for args in [[], [archive.as_posix()], [archive.as_posix(), 'radar_restore_manual']]:
        result, log = run('restore-database.sh', *args)
        assert result.returncode != 0 and not log


def test_restore_refuses_application_database(alias):
    run, archive, _ = alias
    result, log = run('restore-database.sh', archive.as_posix(), 'radar_test', RESTORE_CONFIRM='radar_test')
    assert result.returncode != 0 and not log


def test_restore_refuses_existing_target(alias):
    run, archive, _ = alias
    result, log = run('restore-database.sh', archive.as_posix(), 'radar_restore_manual',
                      RESTORE_CONFIRM='radar_restore_manual', MOCK_CREATE_STATUS='1')
    assert result.returncode != 0
    assert 'create' in log and len([line for line in log.splitlines() if line.startswith('restore ')]) == 1
    assert '--clean' not in log and '--single-transaction' not in log


def test_restore_failure_is_nonzero_and_transactional(alias):
    run, archive, _ = alias
    result, log = run('restore-database.sh', archive.as_posix(), 'radar_restore_manual',
                      RESTORE_CONFIRM='radar_restore_manual', MOCK_RESTORE_STATUS='1')
    assert result.returncode != 0
    assert '--exit-on-error --single-transaction --no-owner --no-privileges' in log
    assert '--clean' not in log

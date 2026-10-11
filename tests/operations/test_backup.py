"""Exercise safety paths with shell-function mocks, never a PostgreSQL server."""
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
BASH = Path("C:/Program Files/Git/bin/bash.exe")
if not BASH.exists():
    BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(not BASH, reason="Bash unavailable")


@pytest.fixture
def shell(tmp_path):
    mocks = tmp_path / "mocks.sh"
    log = tmp_path / "commands.log"
    archive = tmp_path / "safe.dump"
    archive.write_text("fake-archive")
    mocks.write_text('''
pg_dump() {
  printf 'pg_dump\\n' >> "$MOCK_LOG"
  while (( $# )); do
    if [[ "$1" == -f ]]; then printf 'archive' > "$2"; return 0; fi
    shift
  done
}
pg_restore() { printf 'pg_restore %s\\n' "$*" >> "$MOCK_LOG"; return "${MOCK_RESTORE_STATUS:-0}"; }
createdb() { printf 'createdb %s\\n' "$*" >> "$MOCK_LOG"; return "${MOCK_CREATE_STATUS:-0}"; }
dropdb() { printf 'dropdb %s\\n' "$*" >> "$MOCK_LOG"; }
psql() { printf 'psql %s\\n' "$*" >> "$MOCK_LOG"; printf '%s\\n' "${MOCK_TABLE_FOUND:-t}"; }
''', newline="\n")
    env = dict(os.environ, BASH_ENV=mocks.as_posix(), MOCK_LOG=log.as_posix(),
               PGHOST="isolated.invalid", PGUSER="test_user", PGPORT="5432",
               PGDATABASE="test_db", BACKUP_DIR=(tmp_path / "backups").as_posix())

    def run(script, **updates):
        result = subprocess.run([str(BASH), str(ROOT / "infrastructure/backup" / script), archive.as_posix()],
                                env=dict(env, **updates), capture_output=True, text=True)
        return result, log.read_text() if log.exists() else ""
    return run


def test_restore_requires_confirmation_before_database_commands(shell):
    result, log = shell("restore_pg.sh", TARGET_DB="radar_restore_manual", RESTORE_CONFIRM="wrong")
    assert result.returncode != 0
    assert "createdb" not in log and "pg_restore" not in log


def test_restore_refuses_existing_target(shell):
    result, log = shell("restore_pg.sh", TARGET_DB="radar_restore_manual",
                        RESTORE_CONFIRM="radar_restore_manual", MOCK_CREATE_STATUS="1")
    assert result.returncode != 0
    assert "createdb" in log
    assert log.count("pg_restore") == 1  # archive validation only
    assert "dropdb" not in log and "--clean" not in log


def test_restore_refuses_normal_application_database(shell):
    result, log = shell("restore_pg.sh", TARGET_DB="hackathon_radar", RESTORE_CONFIRM="hackathon_radar")
    assert result.returncode != 0
    assert not log


def test_restore_is_transactional_without_destructive_clean(shell):
    result, log = shell("restore_pg.sh", TARGET_DB="radar_restore_manual", RESTORE_CONFIRM="radar_restore_manual")
    assert result.returncode == 0, result.stderr
    assert "--single-transaction" in log and "--exit-on-error" in log
    assert "--clean" not in log and "dropdb" not in log


def test_restore_test_cleans_only_its_new_database(shell):
    result, log = shell("restore_test.sh")
    assert result.returncode == 0, result.stderr
    assert "revoked_tokens" in log
    created = next(line for line in log.splitlines() if line.startswith("createdb"))
    dropped = next(line for line in log.splitlines() if line.startswith("dropdb"))
    assert created.split()[-1] == dropped.split()[-1]
    assert created.split()[-1].startswith("radar_restore_test_")


def test_restore_test_does_not_drop_on_create_failure(shell):
    result, log = shell("restore_test.sh", MOCK_CREATE_STATUS="1")
    assert result.returncode != 0
    assert "dropdb" not in log


def test_restore_test_fails_for_missing_auth_schema(shell):
    result, log = shell("restore_test.sh", MOCK_TABLE_FOUND="f")
    assert result.returncode != 0
    assert "dropdb" in log


def test_backup_verifies_archive_before_publishing(shell):
    result, log = shell("backup_pg.sh")
    assert result.returncode == 0, result.stderr
    assert "pg_dump" in log and "pg_restore --list" in log


@pytest.mark.parametrize("value", ["../database", "bad;name", "--help"])
def test_backup_refuses_unsafe_database_identifier(shell, value):
    result, log = shell("backup_pg.sh", PGDATABASE=value)
    assert result.returncode != 0
    assert not log

"""Rollback safety and HTTP contracts; no Kubernetes or network operations."""
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]
BASH = Path('C:/Program Files/Git/bin/bash.exe')
if not BASH.exists():
    BASH = shutil.which('bash')
spec = importlib.util.spec_from_file_location('rollback_smoke', ROOT / 'scripts/verify_post_rollback.py')
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)
SHA = 'a' * 40


@pytest.fixture
def shell(tmp_path):
    if not BASH:
        pytest.skip('Bash unavailable')
    log = tmp_path / 'calls.log'
    mocks = tmp_path / 'mocks.sh'
    mocks.write_text('''
command() {
  if [[ "${MOCK_NO_KUBECTL:-0}" == 1 && "$*" == '-v kubectl' ]]; then return 1; fi
  builtin command "$@"
}
kubectl() {
  printf 'kubectl %s\\n' "$*" >> "$MOCK_LOG"
  case "$*" in
    *"set image"*) return "${MOCK_SET_STATUS:-0}";;
    *"rollout status"*) return "${MOCK_ROLLOUT_STATUS:-0}";;
    *"get deployment/"*) printf '%s' "$MOCK_IMAGE";;
  esac
}
''', newline='\n')
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    python = bin_dir / 'python'
    python.write_text('''#!/usr/bin/env bash
printf 'verify %s\\n' "$*" >> "$MOCK_LOG"
if [[ "${2:-}" == --validate-only ]]; then exit "${MOCK_VALIDATE_STATUS:-0}"; fi
exit "${MOCK_HTTP_STATUS:-0}"
''', newline='\n')
    python.chmod(0o755)
    env = {**os.environ, 'PATH': bin_dir.as_posix() + os.pathsep + os.environ['PATH'],
           'BASH_ENV': mocks.as_posix(), 'MOCK_LOG': log.as_posix(),
           'KUBE_CONTEXT': 'isolated-test', 'VERIFY_BASE_URL': 'https://staging.example.com',
           'ROLLBACK_CONFIRM': f'isolated-test/hackathon-staging/backend/{SHA}',
           'SCHEMA_COMPATIBILITY_CONFIRMED': SHA,
           'MOCK_IMAGE': f'ghcr.io/hackathonradarfinder/hackathonrdarfinder/backend:{SHA}'}
    def run(args=None, **changes):
        result = subprocess.run([str(BASH), str(ROOT / 'scripts/rollback-deployment.sh'),
            *(args if args is not None else ['staging', 'backend', SHA])],
            env={**env, **changes}, cwd=tmp_path, capture_output=True, text=True, timeout=10)
        return result, log.read_text() if log.exists() else ''
    return run


@pytest.mark.parametrize('args', [[], ['production', 'backend', SHA], ['staging', 'all', SHA], ['staging', 'backend', 'latest']])
def test_invalid_targets_do_not_reach_tools(shell, args):
    result, log = shell(args)
    assert result.returncode != 0 and log == ''


@pytest.mark.parametrize('changes', [{'ROLLBACK_CONFIRM': 'wrong'}, {'SCHEMA_COMPATIBILITY_CONFIRMED': ''}])
def test_approval_and_schema_confirmation_precede_mutation(shell, changes):
    result, log = shell(**changes)
    assert result.returncode != 0 and log == ''


def test_bad_verification_configuration_stops_before_mutation(shell):
    result, log = shell(MOCK_VALIDATE_STATUS='1')
    assert result.returncode != 0 and 'kubectl' not in log


def test_missing_kubectl_never_simulates_rollback(shell):
    result, log = shell(MOCK_NO_KUBECTL='1')
    assert result.returncode != 0 and log == ''


def test_cli_smoke_failure_does_not_print_sensitive_details(monkeypatch, capsys):
    monkeypatch.setenv('VERIFY_BASE_URL', 'https://staging.example.com')
    def fail(_origin):
        raise ValueError('private database connection details')
    monkeypatch.setattr(smoke, 'verify', fail)
    assert smoke.main([]) == 1
    captured = capsys.readouterr()
    assert captured.out == '' and 'private' not in captured.err


@pytest.mark.parametrize('changes', [
    {'MOCK_SET_STATUS': '1'}, {'MOCK_ROLLOUT_STATUS': '1'},
    {'MOCK_IMAGE': 'wrong'}, {'MOCK_HTTP_STATUS': '1'},
])
def test_operational_failures_are_not_simulated_success(shell, changes):
    result, _ = shell(**changes)
    assert result.returncode != 0
    assert 'Application rollout and HTTP catalog checks passed' not in result.stdout


def test_explicit_context_sha_rollout_and_http_checks_from_other_cwd(shell):
    result, log = shell()
    assert result.returncode == 0, result.stderr
    assert f'backend=ghcr.io/hackathonradarfinder/hackathonrdarfinder/backend:{SHA}' in log
    assert all('--context isolated-test -n hackathon-staging' in line for line in log.splitlines() if line.startswith('kubectl'))
    assert 'rollout status deployment/backend --timeout=300s' in log
    assert not any(word in log for word in ('alembic', 'pg_restore', 'redis-cli', 'delete', 'down -v'))


def test_frontend_rollback_requires_confirmation_but_no_schema_flag(shell):
    result, _ = shell(['staging', 'frontend', SHA],
        ROLLBACK_CONFIRM=f'isolated-test/hackathon-staging/frontend/{SHA}', SCHEMA_COMPATIBILITY_CONFIRMED='',
        MOCK_IMAGE=f'ghcr.io/hackathonradarfinder/hackathonrdarfinder/frontend:{SHA}')
    assert result.returncode == 0, result.stderr


class Response(io.BytesIO):
    status = 200


class Opener:
    def __init__(self, changes=None):
        self.changes = changes or {}
        self.calls = []
    def open(self, request, timeout):
        self.calls.append((request.full_url, timeout))
        path = request.full_url.removeprefix('https://staging.example.com')
        values = {'/health': b'ok\n', '/api/health': b'{"status":"healthy"}',
                  '/api/events/?page=1&page_size=1': json.dumps({'data': [], 'total': 0, 'page': 1, 'page_size': 1}).encode(),
                  '/': b'<html><div id="root"></div></html>'}
        body = self.changes.get(path, values[path])
        if isinstance(body, Exception):
            raise body
        return Response(body)


def test_smoke_checks_deployed_health_database_and_spa_shell():
    opener = Opener()
    smoke.verify('https://staging.example.com/', opener)
    assert len(opener.calls) == 4 and all(timeout == 15 for _, timeout in opener.calls)


@pytest.mark.parametrize('changes', [
    {'/health': b'error'}, {'/api/health': b'{"status":"unhealthy"}'},
    {'/api/events/?page=1&page_size=1': b'{"detail":"database error"}'},
    {'/': b'not an app'}, {'/api/health': TimeoutError()},
])
def test_smoke_rejects_health_database_frontend_and_network_failures(changes):
    with pytest.raises((ValueError, TimeoutError)):
        smoke.verify('https://staging.example.com', Opener(changes))


@pytest.mark.parametrize('value', [None, 'http://example.com', 'https://user:secret@example.com',
    'https://example.com/?token=secret', 'https://example.com/#fragment', 'https://example.com/path', 'https://example.com\n'])
def test_origin_rejects_credentials_and_unsupported_configuration(value):
    with pytest.raises(ValueError):
        smoke.validate_origin(value)


def test_smoke_refuses_redirects():
    with pytest.raises(ValueError):
        smoke.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://other.example.com')

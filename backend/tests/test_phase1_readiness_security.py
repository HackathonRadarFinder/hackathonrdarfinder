"""Read-only startup and sanitized failures; temporary resources only."""
from unittest.mock import Mock

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import OperationalError

from app.core.exceptions import AppException
from app.main import app
from app.services.readiness import check_readiness
from app.services.auth_service import AuthService
from workers import check_ready


def test_readiness_never_creates_missing_schema(tmp_path):
    engine = create_engine(f"sqlite:///{(tmp_path / 'empty.db').as_posix()}")
    try:
        try:
            check_readiness(engine)
        except AppException as error:
            assert error.code == 'DATABASE_NOT_READY'
        else:
            raise AssertionError('Missing schema cannot be ready')
        assert inspect(engine).get_table_names() == []
    finally:
        engine.dispose()


def test_readiness_connectivity_errors_are_generic():
    target = Mock()
    target.connect.side_effect = OperationalError('select', {'password': 'synthetic-secret'}, Exception('synthetic-secret'))
    try:
        check_readiness(target)
    except AppException as error:
        assert error.code == 'DATABASE_NOT_READY'
        assert 'synthetic-secret' not in error.message


def test_startup_retries_are_bounded_and_stale_schema_fails_without_retry(monkeypatch):
    probe, sleep = Mock(), Mock()
    monkeypatch.setattr(check_ready, 'check_readiness', probe)
    unavailable = AppException(code='DATABASE_NOT_READY', message='Unavailable', status_code=503)
    probe.side_effect = [unavailable, unavailable, {'status': 'ready'}]
    assert check_ready.wait_until_ready(object(), sleep=sleep)
    assert probe.call_count == 3 and sleep.call_count == 2
    probe.reset_mock(); sleep.reset_mock()
    probe.side_effect = AppException(code='SCHEMA_NOT_READY', message='Migrations required', status_code=503)
    assert not check_ready.wait_until_ready(object(), sleep=sleep)
    assert probe.call_count == 1 and not sleep.called
    probe.reset_mock(); sleep.reset_mock()
    probe.side_effect = unavailable
    assert not check_ready.wait_until_ready(object(), sleep=sleep)
    assert probe.call_count == 3 and sleep.call_count == 2


def test_unexpected_auth_error_does_not_log_credentials_or_exception_text(monkeypatch, caplog):
    def fail(*args):
        raise RuntimeError('synthetic-private-marker database password or token')
    monkeypatch.setattr(AuthService, 'authenticate_user', fail)
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post('/auth/login?token=synthetic-private-marker',
            json={'email': 'fixture@example.com', 'password': 'synthetic-private-marker'},
            headers={'Authorization': 'Bearer synthetic-private-marker'})
    assert response.status_code == 500
    assert response.json()['code'] == 'INTERNAL_SERVER_ERROR'
    assert 'synthetic-private-marker' not in response.text
    app_logs = '\n'.join(record.getMessage() for record in caplog.records if record.name.startswith('app.'))
    assert 'synthetic-private-marker' not in app_logs
    assert 'RuntimeError' in app_logs


def test_request_id_is_bounded_and_control_safe():
    with TestClient(app) as client:
        for value in ('x' * 1000, 'request with spaces', 'request\tlog'):
            response = client.get('/health', headers={'X-Request-ID': value})
            assert response.status_code == 200
            assert response.headers['X-Request-ID'] != value
            assert len(response.headers['X-Request-ID']) <= 64


def test_invalid_startup_settings_do_not_echo_database_credentials():
    from pydantic import ValidationError
    from app.core.config import Settings
    try:
        Settings(DATABASE_URL='postgresql://fixture:synthetic-private-marker@db/fixture', SECRET_KEY='short')
    except ValidationError as error:
        assert 'synthetic-private-marker' not in str(error)
        assert 'input_value' not in str(error)
    else:
        raise AssertionError('Short signing key must fail validation')

"""OTP recovery tests use only a disposable SQLite DB and a fake sender."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.models
from app.main import app
from app.core.database import Base, get_db
from app.models.password_reset_otp import PasswordResetOTP
from app.services import password_reset_service as reset


@pytest.fixture
def recovery(tmp_path, monkeypatch):
    engine = create_engine(
        f"sqlite+pysqlite:///{(tmp_path / 'otp-recovery.db').as_posix()}",
        connect_args={'check_same_thread': False}
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False)
    previous = app.dependency_overrides.get(get_db)

    def override():
        with session_factory() as db:
            yield db

    app.dependency_overrides[get_db] = override
    monkeypatch.setattr(reset.settings, 'PASSWORD_RESET_OTP_ENABLED', True)
    deliveries = []
    monkeypatch.setattr(reset, 'send_otp', lambda email, code: deliveries.append((email, code)) or True)
    try:
        with TestClient(app) as client:
            yield client, session_factory, deliveries
    finally:
        if previous is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous
        engine.dispose()


def register(client):
    response = client.post('/auth/register', json={
        'name': 'Demo Student', 'email': 'student@example.com', 'password': 'OriginalPassword123!'})
    assert response.status_code == 201, response.text


def test_reset_request_is_non_enumerating_and_never_exposes_code(recovery):
    client, sessions, deliveries = recovery
    unknown = client.post('/auth/password-reset/request', json={'email':'missing@example.com'})
    assert unknown.status_code == 200
    assert not deliveries
    register(client)
    known = client.post('/auth/password-reset/request', json={'email':'STUDENT@example.com'})
    assert known.status_code == 200
    assert known.json() == unknown.json()
    assert len(deliveries) == 1
    code = deliveries[0][1]
    assert len(code) == 6 and code.isdecimal()
    assert code not in known.text
    with sessions() as db:
        row = db.scalar(select(PasswordResetOTP))
        assert row is not None
        assert row.code_digest != code and len(row.code_digest) == 64
        assert row.email_key != 'student@example.com'
    assert client.post('/auth/password-reset/request', json={'email':'student@example.com'}).status_code == 200
    assert len(deliveries) == 1  # Cooldown prevents flooding.


def test_reset_changes_password_and_invalidates_previous_jwts(recovery):
    client, _, deliveries = recovery
    register(client)
    login = client.post('/auth/login', json={'email':'student@example.com','password':'OriginalPassword123!'})
    assert login.status_code == 200
    header = {'Authorization':'Bearer ' + login.json()['access_token']}
    assert client.get('/auth/me', headers=header).status_code == 200
    assert client.post('/auth/password-reset/request', json={'email':'student@example.com'}).status_code == 200
    code = deliveries[-1][1]
    result = client.post('/auth/password-reset/confirm', json={
        'email':'student@example.com','code':code,'new_password':'CompletelyNewPassword456!'})
    assert result.status_code == 200, result.text
    assert client.get('/auth/me', headers=header).status_code == 401
    assert client.post('/auth/login', json={'email':'student@example.com','password':'OriginalPassword123!'}).status_code == 401
    assert client.post('/auth/login', json={'email':'student@example.com','password':'CompletelyNewPassword456!'}).status_code == 200
    assert client.post('/auth/password-reset/confirm', json={
        'email':'student@example.com','code':code,'new_password':'OtherNewPassword456!'}).status_code == 400


def test_attempt_limit_and_validation(recovery):
    client, _, deliveries = recovery
    register(client)
    client.post('/auth/password-reset/request', json={'email':'student@example.com'})
    code = deliveries[-1][1]
    wrong = '000000' if code != '000000' else '111111'
    for _ in range(5):
        assert client.post('/auth/password-reset/confirm', json={
            'email':'student@example.com','code':wrong,'new_password':'NewPassword567891!'}).status_code == 400
    assert client.post('/auth/password-reset/confirm', json={
        'email':'student@example.com','code':code,'new_password':'NewPassword567891!'}).status_code == 400
    assert client.post('/auth/password-reset/confirm', json={
        'email':'student@example.com','code':'123','new_password':'NewPassword567891!'}).status_code == 422
    assert client.post('/auth/password-reset/confirm', json={
        'email':'student@example.com','code':code,'new_password':'short'}).status_code == 422


def test_disabled_otp_does_not_send(recovery, monkeypatch):
    client, _, deliveries = recovery
    monkeypatch.setattr(reset.settings, 'PASSWORD_RESET_OTP_ENABLED', False)
    register(client)
    response = client.post('/auth/password-reset/request', json={'email':'student@example.com'})
    assert response.status_code == 503
    assert not deliveries

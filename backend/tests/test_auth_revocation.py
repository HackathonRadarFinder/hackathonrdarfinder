from datetime import datetime, timedelta, timezone
import importlib
import subprocess
import sys
import uuid
from pathlib import Path

import jwt
import pytest
from sqlalchemy import create_engine, inspect, select, text

from app.api import deps
from app.core.config import settings
from app.core.database import get_db
from app.main import app
from app.models.revoked_token import RevokedToken
from app.models.core import Role, User
from test_auth import client, register_user


def login_token(client):
    response = client.post('/auth/login', json={
        'email': 'student@example.com', 'password': 'SecurePassword123!',
    })
    assert response.status_code == 200
    return response.json()['access_token']


def test_revocation_survives_cleared_memory_and_connections(client):
    assert register_user(client).status_code == 201
    token = login_token(client)
    other_token = login_token(client)
    headers = {'Authorization': f'Bearer {token}'}
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
    assert client.post('/auth/logout', headers=headers).status_code == 200

    iterator = app.dependency_overrides[get_db]()
    db = next(iterator)
    try:
        record = db.get(RevokedToken, payload['jti'])
        assert record is not None
        assert record.expires_at.replace(tzinfo=timezone.utc).timestamp() == payload['exp']
        assert record.revoked_at is not None
        assert db.scalars(select(RevokedToken)).all() == [record]
        assert set(RevokedToken.__table__.columns.keys()) == {'jti', 'expires_at', 'revoked_at'}
    finally:
        iterator.close()

    # Clear module state and pooled connections, then read the same file DB.
    importlib.reload(deps)
    client.test_engine.dispose()
    assert client.get('/auth/me', headers=headers).status_code == 401
    assert client.get('/auth/admin-only', headers=headers).status_code == 401
    assert client.post('/auth/logout', headers=headers).status_code == 401
    assert client.get('/auth/me', headers={
        'Authorization': f'Bearer {other_token}',
    }).status_code == 200


@pytest.mark.parametrize('change', [
    'missing_exp', 'missing_sub', 'missing_jti', 'missing_type', 'missing_role',
    'refresh_type', 'invalid_sub', 'empty_jti', 'long_jti', 'string_exp',
    'boolean_exp', 'unsigned',
])
def test_reject_invalid_jwt_claims(client, change):
    payload = {
        'sub': str(uuid.uuid4()), 'role': 'user', 'jti': str(uuid.uuid4()),
        'type': 'access',
        'exp': int((datetime.now(timezone.utc) + timedelta(minutes=10)).timestamp()),
    }
    if change.startswith('missing_'):
        payload.pop(change.removeprefix('missing_'))
    else:
        updates = {
            'refresh_type': ('type', 'refresh'), 'invalid_sub': ('sub', 'invalid'),
            'empty_jti': ('jti', ''), 'long_jti': ('jti', 'a' * 37),
            'string_exp': ('exp', str(payload['exp'])), 'boolean_exp': ('exp', True),
        }
        if change in updates:
            key, value = updates[change]
            payload[key] = value
    token = jwt.encode(payload, '' if change == 'unsigned' else settings.SECRET_KEY,
                       algorithm='none' if change == 'unsigned' else 'HS256')
    assert client.get('/auth/me', headers={
        'Authorization': f'Bearer {token}',
    }).status_code == 401


def test_migration_roundtrip_isolated_database(tmp_path, monkeypatch):
    database_path = tmp_path / 'migration.db'
    url = f'sqlite+pysqlite:///{database_path.as_posix()}'
    monkeypatch.setenv('DATABASE_URL', url)
    backend = Path(__file__).resolve().parents[1]

    def migrate(*args):
        result = subprocess.run(
            [sys.executable, '-m', 'alembic', *args], cwd=backend,
            capture_output=True, text=True,
        )
        assert result.returncode == 0, result.stderr

    migrate('upgrade', 'head')
    engine = create_engine(url)
    try:
        assert 'revoked_tokens' in inspect(engine).get_table_names()
        assert 'email_deliveries' in inspect(engine).get_table_names()
        with engine.connect() as connection:
            assert connection.scalar(text('SELECT version_num FROM alembic_version')) == 'c8d9e0f1a2b3'
        columns = inspect(engine).get_columns('revoked_tokens')
        assert {column['name'] for column in columns} == {'jti', 'expires_at', 'revoked_at'}
        assert all(not column['nullable'] for column in columns)
    finally:
        engine.dispose()
    migrate('downgrade', 'e5a6b09ae2ec')
    engine = create_engine(url)
    try:
        assert 'revoked_tokens' not in inspect(engine).get_table_names()
        assert 'email_deliveries' not in inspect(engine).get_table_names()
        assert 'users' in inspect(engine).get_table_names()
    finally:
        engine.dispose()
    migrate('upgrade', 'head')


@pytest.mark.parametrize('role', [
    'user', 'visitor', 'institution_coordinator', 'reviewer',
    'source_manager', 'data_scientist', 'administrator',
])
def test_rbac_uses_database_role_not_signed_claim(client, role):
    response = register_user(client)
    assert response.status_code == 201
    iterator = app.dependency_overrides[get_db]()
    db = next(iterator)
    try:
        user = db.scalar(select(User))
        assigned_role = db.scalar(select(Role).where(Role.name == role))
        if assigned_role is None:
            assigned_role = Role(name=role)
        user.roles = [assigned_role]
        db.commit()
    finally:
        iterator.close()
    # A signed administrator claim cannot elevate a database role.
    from app.core.security import create_access_token
    token = create_access_token(response.json()['id'], 'administrator')
    headers = {'Authorization': f'Bearer {token}'}
    for path, required_role in [
        ('admin-only', 'administrator'), ('reviewer-only', 'reviewer'),
        ('source-manager-only', 'source_manager'), ('data-scientist-only', 'data_scientist'),
    ]:
        expected = 200 if role in {'administrator', required_role} else 403
        assert client.get(f'/auth/{path}', headers=headers).status_code == expected


def test_existing_module_endpoints_preserved(client):
    for path in ['/events/', '/organizations/', '/predictions/', '/notifications/',
                 '/admin/status', '/health', '/api/v1/health']:
        assert client.get(path).status_code == 200


def test_concurrent_duplicate_logout_is_safe(client):
    from app.api.routes.auth import logout
    from app.schemas.user import TokenPayload

    assert register_user(client).status_code == 201
    token = login_token(client)
    payload = TokenPayload(**jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256']))
    # Simulate two requests that both validated before either committed.
    for _ in range(2):
        iterator = app.dependency_overrides[get_db]()
        db = next(iterator)
        try:
            assert logout(payload, db)['message'].startswith('Successfully logged out')
        finally:
            iterator.close()

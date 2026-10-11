
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models
from app.main import app
from app.core.database import Base, get_db


@pytest.fixture
def client(tmp_path):
    # Temporary file database, allowing fresh-connection persistence checks.
    # Does NOT use the application's configured DATABASE_URL.
    test_engine = create_engine(
        f"sqlite+pysqlite:///{(tmp_path / 'auth.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )

    Base.metadata.create_all(bind=test_engine)

    TestSessionLocal = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            test_client.test_engine = test_engine
            yield test_client
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(bind=test_engine)
        test_engine.dispose()


def register_user(client, email="student@example.com"):
    return client.post(
        "/auth/register",
        json={
            "name": "Test Student",
            "email": email,
            "password": "SecurePassword123!",
        },
    )


def test_register_and_login(client):
    response = register_user(client)

    assert response.status_code == 201, response.text
    assert response.json()["role"] == "user"
    assert response.json()["email"] == "student@example.com"
    assert "password_hash" not in response.json()

    login = client.post(
        "/auth/login",
        json={
            "email": "student@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login.status_code == 200, login.text

    token = login.json()["access_token"]

    me = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert me.status_code == 200, me.text
    assert me.json()["email"] == "student@example.com"


def test_duplicate_registration(client):
    assert register_user(client).status_code == 201
    assert register_user(client).status_code == 409


def test_prevent_admin_self_registration(client):
    response = client.post(
        "/auth/register",
        json={
            "name": "Fake Admin",
            "email": "fakeadmin@example.com",
            "password": "SecurePassword123!",
            "role": "administrator",
        },
    )

    assert response.status_code == 422


def test_invalid_login(client):
    register_user(client)

    response = client.post(
        "/auth/login",
        json={
            "email": "student@example.com",
            "password": "WrongPassword!",
        },
    )

    assert response.status_code == 401


def test_rbac_denial(client):
    register_user(client)

    login = client.post(
        "/auth/login",
        json={
            "email": "student@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login.status_code == 200, login.text

    token = login.json()["access_token"]

    response = client.get(
        "/auth/admin-only",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_logout_revokes_token(client):
    register_user(client)

    login = client.post(
        "/auth/login",
        json={
            "email": "student@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login.status_code == 200, login.text

    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.post(
        "/auth/logout",
        headers=headers,
    ).status_code == 200

    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 401


def test_expired_jwt_token(client):
    import uuid
    import jwt
    from datetime import datetime, timedelta, timezone
    from app.core.config import settings

    expired_token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "role": "user",
            "jti": str(uuid.uuid4()),
            "type": "access",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"},
    )

    assert response.status_code == 401


def test_invalid_jwt_signature(client):
    import uuid
    import jwt
    from datetime import datetime, timedelta, timezone
    from app.core.config import settings

    forged_token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "role": "administrator",
            "jti": str(uuid.uuid4()),
            "type": "access",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=30),
        },
        "a-completely-different-secret-key-for-testing",
        algorithm=settings.ALGORITHM,
    )

    response = client.get(
        "/auth/admin-only",
        headers={"Authorization": f"Bearer {forged_token}"},
    )

    assert response.status_code == 401


def test_oversized_login_password(client):
    register_user(client)

    response = client.post(
        "/auth/login",
        json={
            "email": "student@example.com",
            "password": "A" * 100,
        },
    )

    assert response.status_code == 401


def test_inactive_user_loses_access(client):
    from sqlalchemy import select
    from app.core.database import get_db
    from app.main import app
    from app.models.core import User

    assert register_user(client).status_code == 201

    login = client.post(
        "/auth/login",
        json={
            "email": "student@example.com",
            "password": "SecurePassword123!",
        },
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get("/auth/me", headers=headers).status_code == 200

    db_iterator = app.dependency_overrides[get_db]()
    db = next(db_iterator)
    try:
        user = db.scalar(
            select(User).where(User.email == "student@example.com")
        )
        assert user is not None
        user.status = "inactive"
        db.commit()
    finally:
        db_iterator.close()

    assert client.get("/auth/me", headers=headers).status_code == 401

    blocked_login = client.post(
        "/auth/login",
        json={
            "email": "student@example.com",
            "password": "SecurePassword123!",
        },
    )
    assert blocked_login.status_code == 403


def test_role_changes_take_effect_immediately(client):
    from sqlalchemy import select
    from app.core.database import get_db
    from app.main import app
    from app.models.core import User, Role

    assert register_user(client).status_code == 201

    login = client.post(
        "/auth/login",
        json={
            "email": "student@example.com",
            "password": "SecurePassword123!",
        },
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    assert client.get(
        "/auth/admin-only", headers=headers
    ).status_code == 403

    # Simulate an authorized administrator changing roles
    # directly in the isolated test database.
    db_iterator = app.dependency_overrides[get_db]()
    db = next(db_iterator)
    try:
        user = db.scalar(
            select(User).where(User.email == "student@example.com")
        )
        assert user is not None

        admin_role = db.scalar(
            select(Role).where(Role.name == "administrator")
        )
        if admin_role is None:
            admin_role = Role(name="administrator")
            db.add(admin_role)

        user.roles.append(admin_role)
        db.commit()
    finally:
        db_iterator.close()

    assert client.get(
        "/auth/admin-only", headers=headers
    ).status_code == 200

    # Revoke administrator privileges in the database.
    db_iterator = app.dependency_overrides[get_db]()
    db = next(db_iterator)
    try:
        user = db.scalar(
            select(User).where(User.email == "student@example.com")
        )
        user.roles = [
            role for role in user.roles
            if role.name != "administrator"
        ]
        db.commit()
    finally:
        db_iterator.close()

    assert client.get(
        "/auth/admin-only", headers=headers
    ).status_code == 403

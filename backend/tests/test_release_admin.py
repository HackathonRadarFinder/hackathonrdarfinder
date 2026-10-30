"""Run only against a fresh in-memory database, including authorization checks."""
import uuid
from types import SimpleNamespace
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from app.core.database import Base, get_db
from app.api.routes.release_admin import router
from app.api.deps import require_admin, get_current_db_user, get_current_user_token
from app.models.core import User, Role, AuditLog, Notification
from app.services.release_admin import assign_role, audit_history, notification_monitor


@pytest.fixture
def db():
    engine = create_engine('sqlite+pysqlite://', poolclass=StaticPool, connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def add_user(db, role='user'):
    row = User(name='Test', email=f'{uuid.uuid4()}@example.com', password_hash='test-only', roles=[Role(name=role)])
    db.add(row); db.commit()
    return row


def test_role_assignment_is_audited_and_self_demotion_blocked(db):
    actor = add_user(db, 'administrator')
    target = add_user(db)
    token = SimpleNamespace(sub=str(actor.id))
    result = assign_role(db, target.id, 'reviewer', token)
    assert result['role'] == 'reviewer'
    assert [role.name for role in target.roles] == ['reviewer']
    assert db.scalar(select(AuditLog)).entity_id == target.id
    with pytest.raises(HTTPException) as exc:
        assign_role(db, actor.id, 'user', token)
    assert exc.value.status_code == 409
    assert audit_history(db, 1)['total'] == 1
    assert audit_history(db, 2)['data'] == []


def test_monitor_reports_real_counts_without_dispatch(db):
    user = add_user(db)
    db.add_all([Notification(user_id=user.id, title='A', message='a', is_read=False),
        Notification(user_id=user.id, title='B', message='b', is_read=True)])
    db.commit()
    result = notification_monitor(db)
    assert result == {'in_app_total': 2, 'in_app_unread': 1, 'email_total': 0,
        'email_by_status': {}, 'dispatch_triggered': False}


def test_all_routes_require_authentication_and_admin_role(db):
    app = FastAPI(); app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as client:
        for path in ['/admin/audit', '/admin/notification-monitor']:
            assert client.get(path).status_code in (401, 403)
        assert client.put(f'/admin/users/{uuid.uuid4()}/role', json={'role': 'reviewer'}).status_code in (401, 403)
        user = add_user(db)
        app.dependency_overrides[get_current_db_user] = lambda: user
        app.dependency_overrides[get_current_user_token] = lambda: SimpleNamespace(jti='test', exp=2000000000)
        assert client.get('/admin/audit').status_code == 403
        assert client.get('/admin/notification-monitor').status_code == 403
        assert client.put(f'/admin/users/{user.id}/role', json={'role': 'administrator'}).status_code == 403


def test_invalid_roles_rejected_before_mutation(db):
    app = FastAPI(); app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[require_admin] = lambda: SimpleNamespace(sub=str(uuid.uuid4()))
    with TestClient(app) as client:
        assert client.put(f'/admin/users/{uuid.uuid4()}/role', json={'role': 'superuser'}).status_code == 422

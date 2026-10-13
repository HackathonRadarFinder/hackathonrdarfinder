"""BE-001 integration coverage with real authentication and an isolated database."""

from datetime import timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, insert, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes import predictions
from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.core import EventVersion, Prediction, Role, SavedItem, User
from app.models.hackathon import Hackathon
from app.models.organization import Organization
from app.schemas.user import UserRole


@pytest.fixture
def api(tmp_path):
    """Every request uses a temporary SQLite DB; foreign keys remain enforced."""
    engine = create_engine(
        f"sqlite+pysqlite:///{(tmp_path / 'events-services.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    failure = {"commit": None, "read": False, "rollbacks": 0, "duplicate_name": None}
    request_sessions = []

    class TestSession(Session):
        def commit(self):
            duplicate_name = failure["duplicate_name"]
            if duplicate_name is not None:
                failure["duplicate_name"] = None
                # Introduce a conflict after the service's existence check. The
                # following ORM flush raises a real database IntegrityError.
                self.execute(insert(Organization).values(name=duplicate_name))
            error = failure["commit"]
            if error is not None:
                failure["commit"] = None
                # Flush real changes first, so a rollback is required to undo them.
                self.flush()
                raise error
            return super().commit()

        def rollback(self):
            failure["rollbacks"] += 1
            return super().rollback()

    @event.listens_for(TestSession, "do_orm_execute")
    def fail_read(_state):
        if failure["read"]:
            failure["read"] = False
            raise SQLAlchemyError("private-database-connection-detail")

    sessions = sessionmaker(bind=engine, class_=TestSession, autoflush=False)
    Base.metadata.create_all(engine)
    users = {}
    headers = {}
    with sessions() as db:
        for role in UserRole:
            user = User(
                name=f"Test {role.value}",
                email=f"{role.value}@example.com",
                password_hash="test-only-hash-must-never-appear-in-responses",
                roles=[Role(name=role.value)],
            )
            db.add(user)
            db.flush()
            users[role.value] = user.id
            token = create_access_token(user.id, role.value)
            headers[role.value] = {"Authorization": f"Bearer {token}"}
        db.commit()

    def override_get_db():
        with sessions() as db:
            request_sessions.append(db)
            yield db

    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield SimpleNamespace(
                client=client,
                engine=engine,
                sessions=sessions,
                users=users,
                headers=headers,
                admin=headers[UserRole.ADMINISTRATOR.value],
                failure=failure,
                request_sessions=request_sessions,
            )
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_override
        engine.dispose()


def create_org(api, name="Example Organization", **fields):
    response = api.client.post(
        "/organizations/", headers=api.admin, json={"name": name, **fields}
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def create_event(api, organization_id, title="Example Hackathon", **fields):
    response = api.client.post(
        "/events/",
        headers=api.admin,
        json={"title": title, "organization_id": organization_id, **fields},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def assert_error(response, status):
    assert response.status_code == status, response.text
    body = response.json()
    assert set(body) == {"code", "message", "details", "request_id", "timestamp"}
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert body["timestamp"]
    assert "private-database" not in response.text
    return body


def test_public_reads_and_admin_crud_preserve_envelopes(api):
    for path in ("/events/", "/organizations/"):
        response = api.client.get(path)
        assert response.status_code == 200
        assert set(response.json()) == {"message", "data"}
        assert response.json()["data"] == []

    org = create_org(api, "  First Org  ", website="https://example.com", location="Pune")
    assert org["name"] == "First Org"
    assert org["website"] == "https://example.com/"
    assert set(org) == {"id", "name", "website", "industry", "location", "description"}

    response = api.client.post(
        "/events/",
        headers=api.admin,
        json={
            "title": "  Autumn Hackathon  ",
            "organization": " First Org ",
            "start_date": "2027-10-11T10:00:00",
            "end_date": "2027-10-12T17:00:00",
            "registration_deadline": "2027-10-10T18:00:00",
            "location": "Pune",
            "mode": "hybrid",
            "prize": "Prizes",
            "description": "A test event",
            "url": "https://example.com/event",
            "source": "manual",
            "scraped_at": "2027-10-01T09:00:00",
        },
    )
    assert response.status_code == 200, response.text
    assert set(response.json()) == {"message", "data"}
    item = response.json()["data"]
    assert item["title"] == "Autumn Hackathon"
    assert item["organization_id"] == org["id"]
    assert item["scraped_at"] == "2027-10-01T09:00:00"
    assert "organization" not in item  # No lazy relationship serialization.
    assert api.client.get(f"/events/{item['id']}").json()["data"] == item
    assert api.client.get("/events/").json()["data"] == [item]

    replacement_org = create_org(api, "Second Org")
    response = api.client.put(
        f"/events/{item['id']}",
        headers=api.admin,
        json={"title": "Updated Event", "organization_id": replacement_org["id"]},
    )
    assert response.status_code == 200, response.text
    updated = response.json()["data"]
    assert updated["title"] == "Updated Event"
    assert updated["organization_id"] == replacement_org["id"]
    assert updated["location"] is None  # PUT is full replacement.
    assert updated["scraped_at"] is None

    response = api.client.put(
        f"/organizations/{org['id']}", headers=api.admin, json={"name": "Renamed Org"}
    )
    assert response.status_code == 200, response.text
    assert response.json()["data"]["name"] == "Renamed Org"
    assert response.json()["data"]["website"] is None
    assert api.client.get(f"/organizations/{org['id']}").json()["data"] == response.json()["data"]

    for path in (f"/events/{item['id']}", f"/organizations/{org['id']}"):
        response = api.client.delete(path, headers=api.admin)
        assert response.status_code == 200, response.text
        assert set(response.json()) == {"message"}
        assert_error(api.client.get(path), 404)


WRITE_REQUESTS = (
    ("POST", "/events/", {"title": "Denied", "organization_id": 1}),
    ("PUT", "/events/1", {"title": "Denied", "organization_id": 1}),
    ("DELETE", "/events/1", None),
    ("POST", "/organizations/", {"name": "Denied"}),
    ("PUT", "/organizations/1", {"name": "Denied"}),
    ("DELETE", "/organizations/1", None),
    ("GET", "/admin/stats", None),
    ("GET", "/admin/events", None),
    ("GET", "/admin/organizations", None),
    ("GET", "/admin/users", None),
    ("DELETE", "/admin/events/1", None),
    ("DELETE", "/admin/organizations/1", None),
)


@pytest.mark.parametrize("role", [role.value for role in UserRole if role != UserRole.ADMINISTRATOR])
def test_all_six_nonadmin_roles_cannot_mutate_or_access_admin(api, role):
    for method, path, payload in WRITE_REQUESTS:
        assert_error(api.client.request(method, path, headers=api.headers[role], json=payload), 403)
    with api.sessions() as db:
        assert db.scalar(select(func.count()).select_from(Hackathon)) == 0
        assert db.scalar(select(func.count()).select_from(Organization)) == 0


def test_all_privileged_endpoints_require_authentication(api):
    for method, path, payload in WRITE_REQUESTS:
        assert_error(api.client.request(method, path, json=payload), 401)


@pytest.mark.parametrize("credential", ["malformed", "expired", "inactive", "revoked", "demoted"])
def test_event_write_enforces_existing_authentication_and_live_roles(api, credential):
    headers = api.admin.copy()
    expected = 401
    if credential == "malformed":
        headers = {"Authorization": "Bearer not-a-jwt"}
    elif credential == "expired":
        token = create_access_token(api.users["administrator"], "administrator", timedelta(minutes=-1))
        headers = {"Authorization": f"Bearer {token}"}
    elif credential == "revoked":
        assert api.client.post("/auth/logout", headers=headers).status_code == 200
        api.engine.dispose()  # A new connection must still see persistent logout.
    else:
        with api.sessions() as db:
            user = db.get(User, api.users["administrator"])
            if credential == "inactive":
                user.status = "inactive"
            else:
                user.roles = [db.scalar(select(Role).where(Role.name == "user"))]
                expected = 403
            db.commit()
    assert_error(api.client.post("/organizations/", headers=headers, json={"name": "Denied"}), expected)
    assert_error(api.client.post("/events/", headers=headers, json={"title": "Denied", "organization_id": 1}), expected)
    assert_error(api.client.get("/admin/users", headers=headers), expected)


def test_admin_lists_counts_and_user_projection(api):
    org = create_org(api)
    item = create_event(api, org["id"])
    assert api.client.get("/admin/status").status_code == 200
    for admin_path, public_path in (("/admin/events", "/events/"), ("/admin/organizations", "/organizations/")):
        response = api.client.get(admin_path, headers=api.admin)
        assert response.status_code == 200, response.text
        assert response.json()["data"] == api.client.get(public_path).json()["data"]
    response = api.client.get("/admin/users", headers=api.admin)
    assert response.status_code == 200, response.text
    users = response.json()["data"]
    assert len(users) == len(UserRole)
    for user in users:
        assert set(user) == {"id", "name", "email", "status", "created_at", "roles"}
        assert user["roles"] == [user["email"].split("@")[0]]
        assert user["status"] == "active"
    assert "password_hash" not in response.text
    assert "test-only-hash" not in response.text
    stats = api.client.get("/admin/stats", headers=api.admin)
    assert stats.status_code == 200, stats.text
    assert stats.json() == {
        "total_events": 1, "total_organizations": 1, "total_users": len(UserRole)
    }
    for path in (f"/admin/events/{item['id']}", f"/admin/organizations/{org['id']}"):
        response = api.client.delete(path, headers=api.admin)
        assert response.status_code == 200, response.text
        assert set(response.json()) == {"message"}


@pytest.mark.parametrize("resource,payload", [("events", {"title": "Missing", "organization_id": 1}), ("organizations", {"name": "Missing"})])
def test_missing_and_invalid_resource_ids(api, resource, payload):
    for method in ("GET", "PUT", "DELETE"):
        kwargs = {"headers": api.admin}
        if method == "PUT":
            kwargs["json"] = payload
        assert_error(api.client.request(method, f"/{resource}/999999", **kwargs), 404)
        for identifier in ("0", "-1", "not-an-integer", "2147483648"):
            assert_error(api.client.request(method, f"/{resource}/{identifier}", **kwargs), 422)
    assert_error(api.client.delete(f"/admin/{resource}/999999", headers=api.admin), 404)
    assert_error(api.client.delete(f"/admin/{resource}/0", headers=api.admin), 422)


@pytest.mark.parametrize("payload", [
    {}, {"title": "Valid"}, {"title": "", "organization_id": 1},
    {"title": "   ", "organization_id": 1}, {"title": "x" * 256, "organization_id": 1},
    {"title": "Valid", "organization": " "}, {"title": "Valid", "organization_id": 0},
    {"title": "Valid", "organization_id": -1}, {"title": "Valid", "organization_id": True},
    {"title": "Valid", "organization_id": 2147483648},
    {"title": "Valid", "organization": "Org", "organization_id": 1},
    {"title": "Valid", "organization": None, "organization_id": None},
    {"title": "Valid", "organization_id": 1, "url": "ftp://example.com/file"},
    {"title": "Valid", "organization_id": 1, "url": "https://example.com/" + "x" * 500},
    {"title": "Valid", "organization_id": 1, "location": "x" * 256},
    {"title": "Valid", "organization_id": 1, "mode": "x" * 51},
    {"title": "Valid", "organization_id": 1, "source": "x" * 101},
    {"title": "Valid", "organization_id": 1, "start_date": "0001-01-01T00:00:00+14:00"},
    {"title": "Valid", "organization_id": 1, "end_date": "9999-12-31T23:59:59-14:00"},
    {"title": "Valid", "organization_id": 1, "start_date": "2027-10-12", "end_date": "2027-10-11"},
])
def test_event_input_validation_is_structured(api, payload):
    assert_error(api.client.post("/events/", headers=api.admin, json=payload), 422)
    assert_error(api.client.put("/events/1", headers=api.admin, json=payload), 422)


@pytest.mark.parametrize("payload", [
    {}, {"name": ""}, {"name": "   "}, {"name": "x" * 256},
    {"name": "Valid", "website": "not-a-url"},
    {"name": "Valid", "website": "https://example.com/" + "x" * 500},
    {"name": "Valid", "industry": "x" * 256},
])
def test_organization_input_validation_is_structured(api, payload):
    assert_error(api.client.post("/organizations/", headers=api.admin, json=payload), 422)
    assert_error(api.client.put("/organizations/1", headers=api.admin, json=payload), 422)


@pytest.mark.parametrize("reference", [{"organization": "Unknown"}, {"organization_id": 999999}])
def test_unknown_organization_rejected_without_partial_event_changes(api, reference):
    org = create_org(api)
    item = create_event(api, org["id"])
    payload = {"title": "Invalid relationship", **reference}
    assert_error(api.client.post("/events/", headers=api.admin, json=payload), 404)
    assert_error(api.client.put(f"/events/{item['id']}", headers=api.admin, json=payload), 404)
    assert api.client.get(f"/events/{item['id']}").json()["data"] == item
    assert len(api.client.get("/events/").json()["data"]) == 1


def test_event_dates_preserve_instant_when_normalized_to_utc(api):
    org = create_org(api)
    item = create_event(
        api, org["id"], start_date="2027-10-11T10:00:00+05:30",
        end_date="2027-10-11T06:00:00Z", scraped_at="2027-10-01T09:00:00+05:30",
    )
    assert item["start_date"] == "2027-10-11T04:30:00"
    assert item["end_date"] == "2027-10-11T06:00:00"
    assert item["scraped_at"] == "2027-10-01T03:30:00"
    assert api.client.get(f"/events/{item['id']}").json()["data"] == item


def test_read_schemas_accept_existing_scraper_rows(api):
    with api.sessions() as db:
        organization = Organization(name="Legacy", website="legacy.example")
        item = Hackathon(title="Legacy event", organization_id=None, url="legacy.example/event")
        db.add_all([organization, item])
        db.commit()
        organization_id, event_id = organization.id, item.id
    assert api.client.get(f"/organizations/{organization_id}").json()["data"]["website"] == "legacy.example"
    assert api.client.get(f"/events/{event_id}").json()["data"]["url"] == "legacy.example/event"
    assert api.client.get("/admin/events", headers=api.admin).status_code == 200


def test_openapi_documents_existing_errors_and_admin_security(api):
    response = api.client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    for method, path, _payload in WRITE_REQUESTS:
        path = path.replace("/events/1", "/events/{event_id}").replace(
            "/organizations/1", "/organizations/{organization_id}"
        )
        operation = schema["paths"][path][method.lower()]
        assert operation["security"] == [{"HTTPBearer": []}]
        assert operation["responses"]["422"]["content"]["application/json"]["schema"] == {
            "$ref": "#/components/schemas/ErrorResponse"
        }
    assert "password_hash" not in schema["components"]["schemas"]["AdminUserResponse"]["properties"]


def test_duplicate_org_create_and_rename_preserve_rows(api):
    first = create_org(api, "First")
    second = create_org(api, "Second")
    assert_error(api.client.post("/organizations/", headers=api.admin, json={"name": " First "}), 400)
    assert_error(api.client.put(f"/organizations/{second['id']}", headers=api.admin, json={"name": "First"}), 400)
    assert api.client.get(f"/organizations/{second['id']}").json()["data"] == second
    assert api.client.put(f"/organizations/{first['id']}", headers=api.admin, json={"name": "First"}).status_code == 200


@pytest.mark.parametrize("method", ["POST", "PUT"])
def test_late_unique_constraint_failure_is_rolled_back(api, method):
    original = create_org(api, "Original")
    before = api.client.get("/organizations/").json()["data"]
    api.failure["duplicate_name"] = "Concurrent name"
    path = "/organizations/" if method == "POST" else f"/organizations/{original['id']}"
    response = api.client.request(method, path, headers=api.admin, json={"name": "Concurrent name"})
    assert_error(response, 400)
    failed_session = api.request_sessions[-1]
    assert api.failure["rollbacks"] >= 1
    assert failed_session.is_active
    assert failed_session.scalar(select(func.count()).select_from(Organization)) == 1
    failed_session.close()
    assert api.client.get("/organizations/").json()["data"] == before
    assert api.client.request(method, path, headers=api.admin, json={"name": "Concurrent name"}).status_code == 200


@pytest.mark.parametrize("prefix", ["", "/admin"])
def test_linked_organization_cannot_be_deleted(api, prefix):
    org = create_org(api)
    item = create_event(api, org["id"])
    assert_error(api.client.delete(f"{prefix}/organizations/{org['id']}", headers=api.admin), 409)
    assert api.client.get(f"/organizations/{org['id']}").status_code == 200
    assert api.client.get(f"/events/{item['id']}").json()["data"]["organization_id"] == org["id"]


@pytest.mark.parametrize("relation", ["saved", "prediction", "version"])
@pytest.mark.parametrize("prefix", ["", "/admin"])
def test_linked_event_cannot_be_deleted(api, relation, prefix):
    org = create_org(api)
    item = create_event(api, org["id"])
    with api.sessions() as db:
        links = {
            "saved": SavedItem(hackathon_id=item["id"], user_id=api.users["user"]),
            "prediction": Prediction(hackathon_id=item["id"], prediction="2027-01-01"),
            "version": EventVersion(hackathon_id=item["id"], version_number=1),
        }
        link = links[relation]
        db.add(link)
        db.commit()
        link_id = link.id
        link_type = type(link)
    assert_error(api.client.delete(f"{prefix}/events/{item['id']}", headers=api.admin), 409)
    assert api.client.get(f"/events/{item['id']}").status_code == 200
    with api.sessions() as db:
        assert db.get(link_type, link_id) is not None


@pytest.mark.parametrize("resource", ["events", "organizations"])
@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE"])
@pytest.mark.parametrize("integrity", [False, True])
def test_failed_commit_rolls_back_and_session_remains_usable(api, resource, method, integrity):
    org = create_org(api)
    if resource == "events":
        item = create_event(api, org["id"])
        payload = {"title": "Changed", "organization_id": org["id"]}
    else:
        item = org
        payload = {"name": "Changed"}
    before = api.client.get(f"/{resource}/").json()["data"]
    error = SQLAlchemyError("private-database-commit-detail")
    if integrity:
        error = IntegrityError("private-database-statement", {}, Exception("constraint"))
    api.failure["commit"] = error
    path = f"/{resource}/" if method == "POST" else f"/{resource}/{item['id']}"
    kwargs = {"headers": api.admin}
    if method != "DELETE":
        kwargs["json"] = payload
    response = api.client.request(method, path, **kwargs)
    expected = (400 if resource == "organizations" and method != "DELETE" else 409) if integrity else 503
    body = assert_error(response, expected)
    if not integrity:
        assert body["code"] == "DATABASE_ERROR"
    failed_session = api.request_sessions[-1]
    assert api.failure["rollbacks"] >= 1
    assert failed_session.is_active
    # A successful query on the exact same Session proves no failed-transaction state.
    assert failed_session.scalar(select(func.count()).select_from(Organization)) == 1
    failed_session.close()
    assert api.client.get(f"/{resource}/").json()["data"] == before
    # A later transaction can succeed after the simulated commit failure.
    create_org(api, "After rollback")


@pytest.mark.parametrize("path", ["/events/", "/events/1", "/organizations/", "/organizations/1"])
def test_database_read_failure_preserves_global_error_contract(api, path):
    api.failure["read"] = True
    body = assert_error(api.client.get(path), 503)
    assert body["code"] == "DATABASE_ERROR"
    assert api.failure["rollbacks"] >= 1
    assert api.client.get("/organizations/").status_code == 200


def test_health_notification_and_prediction_routes_remain_available(api, monkeypatch):
    for path in ("/health", "/api/v1/health"):
        response = api.client.get(path, headers={"X-Request-ID": "be-001-regression"})
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert response.headers["X-Request-ID"] == "be-001-regression"
    assert api.client.get("/notifications/").status_code == 401
    assert api.client.get("/predictions/").json()["models"] == ["baseline", "neural"]
    calls = []

    def predict(**kwargs):
        calls.append(kwargs)
        return {"organization": kwargs["organization"], "predicted_date": "2028-01-01", "confidence": 0.8}

    monkeypatch.setattr(predictions, "baseline_predict", predict)
    monkeypatch.setattr(predictions, "neural_predict", predict)
    payload = {"organization": "Regression Org", "historical_dates": ["2026-01-01", "2027-01-01"]}
    for path in ("/predictions/baseline", "/predictions/neural"):
        response = api.client.post(path, json=payload)
        assert response.status_code == 200, response.text
        assert response.json()["predicted_date"] == "2028-01-01"
    assert calls == [payload, payload]

    def unavailable(**_kwargs):
        raise FileNotFoundError("No test model artifact")

    monkeypatch.setattr(predictions, "neural_predict", unavailable)
    assert_error(api.client.post("/predictions/neural", json=payload), 503)

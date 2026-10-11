"""BE-002 pagination/filtering contracts against an isolated, FK-enabled database."""

from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, get_db
from app.core.security import create_access_token
from app.main import app
from app.models.core import Role, User
from app.models.hackathon import Hackathon
from app.models.organization import Organization


@pytest.fixture
def api(tmp_path):
    engine = create_engine(
        f"sqlite+pysqlite:///{(tmp_path / 'event-pagination.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    failure = {"stage": None, "rollbacks": 0}
    statements = []

    class TestSession(Session):
        def rollback(self):
            failure["rollbacks"] += 1
            return super().rollback()

    @event.listens_for(TestSession, "do_orm_execute")
    def fail_selected_read(state):
        if not state.is_select or failure["stage"] is None:
            return
        sql = str(state.statement).lower()
        if "hackathons" not in sql:
            return
        stage = "count" if "count(" in sql else "page"
        if failure["stage"] == stage:
            failure["stage"] = None
            raise SQLAlchemyError("private-query-detail-must-not-be-exposed")

    @event.listens_for(engine, "before_cursor_execute")
    def record_event_reads(_connection, _cursor, statement, parameters, _context, _many):
        if statement.lstrip().upper().startswith("SELECT") and "hackathons" in statement:
            statements.append((statement, parameters))

    sessions = sessionmaker(bind=engine, class_=TestSession, autoflush=False)
    Base.metadata.create_all(engine)
    with sessions() as db:
        organizations = [Organization(name="First Org"), Organization(name="Second Org")]
        user = User(
            name="Pagination Administrator",
            email="pagination-admin@example.com",
            password_hash="private-test-password-hash",
            roles=[Role(name="administrator")],
        )
        db.add_all([*organizations, user])
        db.flush()
        organization_ids = [organization.id for organization in organizations]
        token = create_access_token(user.id, "administrator")
        db.commit()

    def override_get_db():
        with sessions() as db:
            yield db

    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield SimpleNamespace(
                client=client,
                sessions=sessions,
                engine=engine,
                organization_ids=organization_ids,
                admin={"Authorization": f"Bearer {token}"},
                failure=failure,
                statements=statements,
            )
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_override
        engine.dispose()


def seed(api, count=0, **fields):
    """Insert directly without weakening the API's authentication dependencies."""
    with api.sessions() as db:
        records = [
            Hackathon(
                title=f"Event {index:03}",
                organization_id=api.organization_ids[0],
                **fields,
            )
            for index in range(count)
        ]
        db.add_all(records)
        db.flush()
        ids = [record.id for record in records]
        db.commit()
    return ids


def seed_rows(api, rows):
    with api.sessions() as db:
        records = [
            Hackathon(
                **{
                    "title": f"Filter Event {index}",
                    "organization_id": api.organization_ids[0],
                    **fields,
                }
            )
            for index, fields in enumerate(rows)
        ]
        db.add_all(records)
        db.flush()
        ids = [record.id for record in records]
        db.commit()
    return ids


def page(api, **params):
    response = api.client.get("/events/", params=params)
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"message", "data", "total", "page", "page_size"}
    assert body["message"] == "Events fetched successfully"
    assert isinstance(body["data"], list)
    return body


def ids(body):
    return [item["id"] for item in body["data"]]


def assert_error(response, status):
    assert response.status_code == status, response.text
    body = response.json()
    assert set(body) == {"code", "message", "details", "request_id", "timestamp"}
    assert body["request_id"] == response.headers["X-Request-ID"]
    assert body["timestamp"]
    assert "private-query-detail" not in response.text
    return body


@pytest.mark.parametrize("params", [{}, {"unrelated": "value"}])
def test_legacy_list_remains_unpaginated_and_public(api, params):
    expected = seed(api, 23)
    response = api.client.get("/events/", params=params)
    assert response.status_code == 200, response.text
    body = response.json()
    assert set(body) == {"message", "data"}
    assert body["message"] == "Events fetched successfully"
    assert ids(body) == expected


@pytest.mark.parametrize("count", [0, 1, 10, 23])
def test_explicit_first_page_has_defaults_and_accurate_total(api, count):
    expected = seed(api, count)
    body = page(api, page=1)
    assert ids(body) == expected[:10]
    assert (body["total"], body["page"], body["page_size"]) == (count, 1, 10)


@pytest.mark.parametrize("page_number,expected_slice", [(1, slice(0, 10)), (2, slice(10, 20)), (3, slice(20, 23)), (4, slice(0, 0)), (2_147_483_647, slice(0, 0))])
def test_pages_are_stable_complete_and_allow_out_of_range_pages(api, page_number, expected_slice):
    expected = seed(api, 23)
    first = page(api, page=page_number, page_size=10)
    second = page(api, page=page_number, page_size=10)
    assert first == second
    assert ids(first) == expected[expected_slice]
    assert (first["total"], first["page"], first["page_size"]) == (23, page_number, 10)


@pytest.mark.parametrize("page_size", [1, 7, 100])
def test_explicit_page_size_defaults_to_first_page(api, page_size):
    expected = seed(api, 101)
    body = page(api, page_size=page_size)
    assert ids(body) == expected[:page_size]
    assert (body["total"], body["page"], body["page_size"]) == (101, 1, page_size)


def test_all_pages_cover_each_id_once_despite_gaps_and_duplicate_titles(api):
    expected = seed_rows(api, [{"id": value, "title": "Same title"} for value in (91, 2, 54, 15, 3)])
    seen = []
    for page_number in range(1, 4):
        body = page(api, page=page_number, page_size=2)
        assert body["total"] == 5
        seen.extend(ids(body))
    assert seen == sorted(expected)
    assert len(seen) == len(set(seen))


@pytest.mark.parametrize("field,term", [("location", "  pUnE  "), ("mode", "  oNLiNe  ")])
def test_text_filters_are_trimmed_case_insensitive_substrings(api, field, term):
    match = "Greater PUNE City" if field == "location" else "Hybrid ONLINE event"
    expected = seed_rows(api, [{field: match}, {field: "Different"}, {field: None}])
    body = page(api, **{field: term})
    assert ids(body) == expected[:1]
    assert (body["total"], body["page"], body["page_size"]) == (1, 1, 10)


@pytest.mark.parametrize("field", ["location", "mode"])
@pytest.mark.parametrize(
    "term,matching,nonmatching",
    [
        ("%", "100% Online", "100X Online"),
        ("_", "North_South", "NorthXSouth"),
        ("/", "North/South", "NorthSouth"),
        ("/%_", "North/%_South", "North/ABSouth"),
        ("\\", "North\\South", "NorthSouth"),
    ],
)
def test_sql_like_metacharacters_are_literal(api, field, term, matching, nonmatching):
    expected = seed_rows(api, [{field: matching}, {field: nonmatching}, {field: None}])
    body = page(api, **{field: term})
    assert ids(body) == expected[:1]
    assert body["total"] == 1


def test_organization_filter_is_exact_and_unknown_organization_is_empty(api):
    first, second = api.organization_ids
    expected = seed_rows(api, [{"organization_id": first}, {"organization_id": second}, {"organization_id": None}])
    assert ids(page(api, organization_id=first)) == expected[:1]
    assert ids(page(api, organization_id=second)) == expected[1:2]
    empty = page(api, organization_id=2_147_483_647)
    assert empty["data"] == []
    assert empty["total"] == 0


def test_filters_combine_with_and_and_total_is_counted_before_slicing(api):
    first, second = api.organization_ids
    expected = seed_rows(
        api,
        [
            {"location": "Pune", "mode": "online", "organization_id": first},
            {"location": "Pune", "mode": "offline", "organization_id": first},
            {"location": "Mumbai", "mode": "online", "organization_id": first},
            {"location": "Pune", "mode": "online", "organization_id": second},
            {"location": "Greater PUNE", "mode": "ONLINE", "organization_id": first},
            {"location": "Pune City", "mode": "hybrid online", "organization_id": first},
        ],
    )
    body = page(api, location="pune", mode="online", organization_id=first, page=2, page_size=2)
    assert ids(body) == expected[5:6]
    assert (body["total"], body["page"], body["page_size"]) == (3, 2, 2)
    empty = page(api, location="does not exist", mode="online", organization_id=first)
    assert empty["data"] == []
    assert empty["total"] == 0


@pytest.mark.parametrize(
    "name,value",
    [
        ("page", "0"),
        ("page", "-1"),
        ("page", "2147483648"),
        ("page", "1.5"),
        ("page", "true"),
        ("page", ""),
        ("page_size", "0"),
        ("page_size", "-1"),
        ("page_size", "101"),
        ("page_size", "1.5"),
        ("page_size", "many"),
        ("page_size", ""),
        ("organization_id", "0"),
        ("organization_id", "-1"),
        ("organization_id", "2147483648"),
        ("organization_id", "1.5"),
        ("organization_id", "null"),
        ("organization_id", ""),
        ("location", ""),
        ("location", "   "),
        ("location", "x" * 256),
        ("mode", ""),
        ("mode", "\t \n"),
        ("mode", "x" * 51),
    ],
)
def test_invalid_query_values_return_existing_validation_envelope(api, name, value):
    body = assert_error(api.client.get("/events/", params={name: value}), 422)
    assert body["code"] == "VALIDATION_ERROR"
    assert any(item["loc"] == ["query", name] for item in body["details"])


@pytest.mark.parametrize("field,length", [("location", 255), ("mode", 50)])
def test_maximum_length_text_filter_is_accepted(api, field, length):
    expected = seed_rows(api, [{field: "x" * length}])
    assert ids(page(api, **{field: "x" * length})) == expected


def test_sql_shaped_filter_is_bound_data_and_does_not_expand_results(api):
    term = "Pune%' OR 1=1 --_"
    expected = seed_rows(api, [{"location": term}, {"location": "Pune"}, {"location": "Elsewhere"}])
    api.statements.clear()
    body = page(api, location=term, page_size=1)
    assert ids(body) == expected[:1]
    assert body["total"] == 1
    assert len(api.statements) == 2
    assert all(term not in sql for sql, _parameters in api.statements)
    assert all("OR 1=1" in repr(parameters) for _sql, parameters in api.statements)


def test_pagination_uses_bounded_database_queries_without_loading_all_events(api):
    expected = seed(api, 25)
    api.statements.clear()
    body = page(api, page=2, page_size=7)
    assert ids(body) == expected[7:14]
    assert len(api.statements) == 2
    count_sql, count_params = api.statements[0]
    page_sql, page_params = api.statements[1]
    assert "count(" in count_sql.lower()
    assert "LIMIT" in page_sql and "OFFSET" in page_sql
    assert "ORDER BY hackathons.id" in page_sql
    assert 7 in page_params
    assert count_params == ()


@pytest.mark.parametrize("stage", ["count", "page"])
def test_database_failure_rolls_back_and_keeps_global_error_contract(api, stage):
    expected = seed(api, 2)
    api.failure["stage"] = stage
    body = assert_error(api.client.get("/events/", params={"page": 1}), 503)
    assert body["code"] == "DATABASE_ERROR"
    assert body["message"] == "Unable to complete database operation."
    assert api.failure["rollbacks"] == 1
    assert api.failure["stage"] is None
    assert ids(page(api, page=1)) == expected
    with api.sessions() as db:
        assert db.scalar(select(func.count()).select_from(Hackathon)) == 2


def test_admin_event_list_and_event_detail_contracts_remain_unchanged(api):
    expected = seed(api, 15, location="Pune")
    assert_error(api.client.get("/admin/events"), 401)
    response = api.client.get("/admin/events", headers=api.admin)
    assert response.status_code == 200, response.text
    assert set(response.json()) == {"data"}
    assert ids(response.json()) == expected
    item = page(api, page=2, page_size=10)["data"][0]
    detail = api.client.get(f"/events/{item['id']}")
    assert detail.status_code == 200, detail.text
    assert set(detail.json()) == {"message", "data"}
    assert detail.json()["data"] == item
    assert "private-test-password-hash" not in response.text


def test_openapi_describes_query_bounds_success_variants_and_global_errors(api):
    document = api.client.get("/openapi.json").json()
    operation = document["paths"]["/events/"]["get"]
    parameters = {parameter["name"]: parameter for parameter in operation["parameters"]}
    assert set(parameters) == {"page", "page_size", "location", "mode", "organization_id"}
    assert all(parameter["in"] == "query" and not parameter.get("required", False) for parameter in parameters.values())

    def resolve(schema):
        if "$ref" in schema:
            return document["components"]["schemas"][schema["$ref"].split("/")[-1]]
        return schema

    def concrete(schema):
        return next((item for item in schema.get("anyOf", []) if item.get("type") != "null"), schema)

    for name, maximum in (("page", 2_147_483_647), ("page_size", 100), ("organization_id", 2_147_483_647)):
        schema = concrete(parameters[name]["schema"])
        assert schema["type"] == "integer"
        assert schema.get("minimum") == 1 or schema.get("exclusiveMinimum") == 0
        assert schema["maximum"] == maximum
    for name, maximum in (("location", 255), ("mode", 50)):
        schema = concrete(parameters[name]["schema"])
        assert schema["type"] == "string"
        assert schema["minLength"] == 1
        assert schema["maxLength"] == maximum

    response_schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
    variants = [resolve(item) for item in response_schema.get("anyOf", [response_schema])]
    property_sets = [set(item["properties"]) for item in variants]
    assert {"message", "data"} in property_sets
    assert {"message", "data", "total", "page", "page_size"} in property_sets
    for status in ("422", "503"):
        error = operation["responses"][status]["content"]["application/json"]["schema"]
        assert set(resolve(error)["properties"]) == {"code", "message", "details", "request_id", "timestamp"}

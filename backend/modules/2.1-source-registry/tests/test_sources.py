
import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db
from app.models import Source
import app.routers.sources as sources_router_module


# Separate in-memory database used only for tests
test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine
)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Make API requests use the test database
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_test_database(monkeypatch):
    # Start every test with a clean database
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    # Avoid real network requests to robots.txt during tests
    monkeypatch.setattr(
        sources_router_module,
        "check_robots_txt",
        lambda base_url: (True, "allowed")
    )

    # Add a known active source for tests that use /sources/1
    db = TestingSessionLocal()
    try:
        source = Source(
            source_id=1,
            source_name="Unstop",
            base_url="https://unstop.com/",
            source_type="dynamic",
            tier=1,
            crawl_frequency="6h",
            priority=1,
            is_active=True,
            robots_txt_allowed=True,
            robots_txt_status="allowed",
            created_by="Rajesh"
        )

        db.add(source)
        db.commit()
    finally:
        db.close()

    yield


def test_create_source():
    response = client.post(
        "/sources",
        json={
            "source_name": "Test Source",
            "base_url": "https://example.com/",
            "source_type": "static",
            "tier": 2,
            "crawl_frequency": "24h",
            "priority": 2,
            "created_by": "Rajesh"
        }
    )

    assert response.status_code == 201

    data = response.json()

    assert data["source_name"] == "Test Source"
    assert data["base_url"] == "https://example.com/"
    assert data["source_type"] == "static"
    assert data["tier"] == 2
    assert data["crawl_frequency"] == "24h"
    assert data["priority"] == 2
    assert "source_id" in data


def test_duplicate_source():
    source = {
        "source_name": "Duplicate Test",
        "base_url": "https://duplicate-example.com/",
        "source_type": "static",
        "tier": 1,
        "crawl_frequency": "24h",
        "priority": 1,
        "created_by": "Rajesh"
    }

    first_response = client.post(
        "/sources",
        json=source
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/sources",
        json=source
    )

    assert second_response.status_code == 409


def test_get_sources():
    response = client.get("/sources")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)


def test_get_active_sources():
    response = client.get(
        "/sources?active_only=true"
    )

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, list)

    for source in data:
        assert source["is_active"] is True


def test_get_source_by_id():
    response = client.get("/sources/1")

    assert response.status_code == 200

    data = response.json()

    assert data["source_id"] == 1


def test_update_source():
    response = client.put(
        "/sources/1",
        json={
            "crawl_frequency": "12h"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert data["crawl_frequency"] == "12h"


def test_pause_source():
    response = client.put(
        "/sources/1/pause"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["is_active"] is False


def test_resume_source():
    response = client.put(
        "/sources/1/resume"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["is_active"] is True


def test_update_crawl_time():
    response = client.patch(
        "/sources/1/crawl"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["last_crawled_at"] is not None


def test_source_not_found():
    response = client.get("/sources/99999")

    assert response.status_code == 404

def test_collector_source_contract():
    # Step 1: Get only active sources
    response = client.get(
        "/sources?active_only=true"
    )

    assert response.status_code == 200

    sources = response.json()

    # Step 2: Verify every returned source is active
    for source in sources:
        assert source["is_active"] is True

        # Step 3: Collector needs these fields
        assert "source_id" in source
        assert "base_url" in source

        source_id = source["source_id"]
        base_url = source["base_url"]

        assert isinstance(source_id, int)
        assert isinstance(base_url, str)
        assert base_url.startswith("http")

        # Step 4: Simulate collector updating crawl time
        crawl_response = client.patch(
            f"/sources/{source_id}/crawl"
        )

        assert crawl_response.status_code == 200

        updated_source = crawl_response.json()

        # Step 5: Verify crawl timestamp was updated
        assert updated_source["source_id"] == source_id
        assert updated_source["base_url"] == base_url
        assert updated_source["last_crawled_at"] is not None
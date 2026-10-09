from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/v1/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"
    assert data["service"] == "hackathon-radar-api"
    assert data["version"] == "0.1.0"


def test_request_id_is_generated():
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert "X-Request-ID" in response.headers
    assert response.headers["X-Request-ID"]


def test_request_id_is_preserved():
    request_id = "test-request-123"

    response = client.get(
        "/api/v1/health",
        headers={"X-Request-ID": request_id},
    )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == request_id


def test_not_found_error_format():
    response = client.get("/api/v1/not-real")

    assert response.status_code == 404

    data = response.json()

    assert data["code"] == "HTTP_404"
    assert data["message"] == "Not Found"
    assert data["details"] is None
    assert data["request_id"]
    assert data["timestamp"]
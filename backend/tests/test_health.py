# from fastapi.testclient import TestClient

# from app.main import app

# client = TestClient(app)


# def test_health_endpoint():
#     response = client.get("/health")
#     assert response.status_code == 200
#     payload = response.json()
#     assert payload["status"] == "healthy"
#     assert payload["service"] == "hackathon-radar-api"


from pathlib import Path
import sys

from fastapi.testclient import TestClient

# Add the backend directory to Python's import path
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "healthy"
    assert payload["service"] == "hackathon-radar-api"

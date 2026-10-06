import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_register_and_login_flow():
    # 1. Register a test user
    reg_payload = {
        "name": "Test Engineer",
        "email": "testuser@example.com",
        "password": "SecurePassword@123",
        "role": "user"
    }
    res_reg = client.post("/api/v1/auth/register", json=reg_payload)
    assert res_reg.status_code == 201
    assert res_reg.json()["email"] == "testuser@example.com"
    assert "hashed_password" not in res_reg.json()

    # 2. Duplicate registration should fail (400)
    res_dup = client.post("/api/v1/auth/register", json=reg_payload)
    assert res_dup.status_code == 400

    # 3. Login with valid credentials
    login_payload = {
        "email": "testuser@example.com",
        "password": "SecurePassword@123"
    }
    res_login = client.post("/api/v1/auth/login", json=login_payload)
    assert res_login.status_code == 200
    token = res_login.json()["access_token"]
    assert token is not None

    # 4. Access /me with Bearer token
    headers = {"Authorization": f"Bearer {token}"}
    res_me = client.get("/api/v1/auth/me", headers=headers)
    assert res_me.status_code == 200
    assert res_me.json()["email"] == "testuser@example.com"

def test_rbac_denial():
    # Register regular user
    reg_payload = {
        "name": "Student",
        "email": "student@example.com",
        "password": "Password123!",
        "role": "user"
    }
    client.post("/api/v1/auth/register", json=reg_payload)
    res_login = client.post("/api/v1/auth/login", json={"email": "student@example.com", "password": "Password123!"})
    token = res_login.json()["access_token"]

    # Attempt to hit admin endpoint -> must return 403 Forbidden
    headers = {"Authorization": f"Bearer {token}"}
    res_admin = client.get("/api/v1/auth/admin-only", headers=headers)
    assert res_admin.status_code == 403
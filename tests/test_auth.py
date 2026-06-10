import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture(autouse=True)
def setup_database():
    from main import Base, engine
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

def test_user_registration_and_auth_flow():
    # Since TestClient fixture has headers set, let's construct a clean one without headers
    with TestClient(app) as anonymous_client:
        # 1. Unauthenticated request to /users/me should fail
        resp = anonymous_client.get("/users/me")
        assert resp.status_code == 401
        assert "Missing X-API-Key" in resp.text

        # 2. Register user
        reg_resp = anonymous_client.post("/users/register", json={
            "email": "testuser@driftguard.com",
            "name": "Test User"
        })
        assert reg_resp.status_code == 200
        data = reg_resp.json()
        assert "api_key" in data
        assert data["email"] == "testuser@driftguard.com"
        api_key = data["api_key"]

        # 3. Requesting with invalid key fails
        resp = anonymous_client.get("/users/me", headers={"X-API-Key": "invalid-key"})
        assert resp.status_code == 401

        # 4. Requesting with valid key succeeds
        auth_headers = {"X-API-Key": api_key}
        profile_resp = anonymous_client.get("/users/me", headers=auth_headers)
        assert profile_resp.status_code == 200
        profile_data = profile_resp.json()
        assert profile_data["email"] == "testuser@driftguard.com"
        assert profile_data["name"] == "Test User"

        # 5. Rotate key
        rotate_resp = anonymous_client.post("/users/users/rotate-key" if False else "/users/rotate-key", headers=auth_headers)
        assert rotate_resp.status_code == 200
        rotate_data = rotate_resp.json()
        new_key = rotate_data["api_key"]
        assert new_key != api_key

        # 6. Old key fails now
        old_resp = anonymous_client.get("/users/me", headers={"X-API-Key": api_key})
        assert old_resp.status_code == 401

        # 7. New key works
        new_resp = anonymous_client.get("/users/me", headers={"X-API-Key": new_key})
        assert new_resp.status_code == 200

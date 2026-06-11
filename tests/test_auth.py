import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture(autouse=True)
def setup_database():
    import os
    import main
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from main import Base

    test_db_url = "sqlite:///test_driftguard_metadata_auth.db"
    test_engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    
    orig_engine = main.engine
    orig_session = main.SessionLocal
    
    main.engine = test_engine
    main.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    Base.metadata.create_all(bind=test_engine)
    
    yield
    
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()
    if os.path.exists("test_driftguard_metadata_auth.db"):
        try:
            os.remove("test_driftguard_metadata_auth.db")
        except Exception:
            pass
            
    main.engine = orig_engine
    main.SessionLocal = orig_session

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

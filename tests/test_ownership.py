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

    test_db_url = "sqlite:///test_driftguard_metadata_owner.db"
    test_engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    
    orig_engine = main.engine
    orig_session = main.SessionLocal
    
    main.engine = test_engine
    main.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    Base.metadata.create_all(bind=test_engine)
    
    yield
    
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()
    if os.path.exists("test_driftguard_metadata_owner.db"):
        try:
            os.remove("test_driftguard_metadata_owner.db")
        except Exception:
            pass
            
    main.engine = orig_engine
    main.SessionLocal = orig_session

def test_cross_user_model_access_prevention():
    with TestClient(app) as client:
        # User A
        reg_a = client.post("/users/register", json={"email": "own_a@driftguard.com", "name": "Owner A"})
        key_a = reg_a.json()["api_key"]
        headers_a = {"X-API-Key": key_a}

        # User B
        reg_b = client.post("/users/register", json={"email": "own_b@driftguard.com", "name": "Owner B"})
        key_b = reg_b.json()["api_key"]
        headers_b = {"X-API-Key": key_b}

        # User A creates Project A
        proj_a = client.post("/projects", json={"name": "Proj A"}, headers=headers_a).json()
        proj_a_id = proj_a["id"]

        # User B creates Project B
        proj_b = client.post("/projects", json={"name": "Proj B"}, headers=headers_b).json()
        proj_b_id = proj_b["id"]

        # 1. User B tries to register model under User A's project (fails with 403)
        reg_fail = client.post("/register", json={
            "model_id": "model-a",
            "project_id": proj_a_id,
            "drift_threshold": 0.25,
            "features": ["f1"]
        }, headers=headers_b)
        assert reg_fail.status_code == 403

        # 2. User A successfully registers model under Project A
        reg_success = client.post("/register", json={
            "model_id": "model-a",
            "project_id": proj_a_id,
            "drift_threshold": 0.25,
            "features": ["f1"]
        }, headers=headers_a)
        assert reg_success.status_code == 200

        # 3. User B successfully registers THEIR OWN model-a under Project B (uniqueness composite check passes)
        reg_b_success = client.post("/register", json={
            "model_id": "model-a",
            "project_id": proj_b_id,
            "drift_threshold": 0.15,
            "features": ["f2"]
        }, headers=headers_b)
        assert reg_b_success.status_code == 200

        # 4. User B posts predictions to THEIR OWN model-a (succeeds with 200)
        pred_success = client.post("/predict/model-a", json={
            "features": [1.0],
            "prediction": [0.0],
            "drift_score": 0.05
        }, headers=headers_b)
        assert pred_success.status_code == 200

        # 5. Verify User B's model details return THEIR OWN threshold (0.15) and NOT User A's (0.25)
        model_b_details = client.get("/models/model-a", headers=headers_b)
        assert model_b_details.status_code == 200
        assert model_b_details.json()["drift_threshold"] == 0.15

        # 6. Verify User A's model details return User A's threshold (0.25)
        model_a_details = client.get("/models/model-a", headers=headers_a)
        assert model_a_details.status_code == 200
        assert model_a_details.json()["drift_threshold"] == 0.25

        # 7. Verify that querying a non-existent model ID returns 404 for User B
        non_existent_resp = client.get("/models/non-existent-model", headers=headers_b)
        assert non_existent_resp.status_code == 404

import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture(autouse=True)
def setup_database():
    from main import Base, engine
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)

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
            "model_id": "cross-model",
            "project_id": proj_a_id,
            "drift_threshold": 0.15,
            "features": ["f1"]
        }, headers=headers_b)
        assert reg_fail.status_code == 403

        # 2. User A successfully registers model under Project A
        reg_success = client.post("/register", json={
            "model_id": "model-a",
            "project_id": proj_a_id,
            "drift_threshold": 0.15,
            "features": ["f1"]
        }, headers=headers_a)
        assert reg_success.status_code == 200

        # 3. User B tries to post predictions to User A's model (fails with 403)
        pred_fail = client.post("/predict/model-a", json={
            "features": [1.0],
            "prediction": [0.0],
            "drift_score": 0.05
        }, headers=headers_b)
        assert pred_fail.status_code == 403

        # 4. User B tries to view User A's model details, versions, drift, retraining history, or audit logs
        assert client.get("/models/model-a", headers=headers_b).status_code == 403
        assert client.get("/models/model-a/versions", headers=headers_b).status_code == 403
        assert client.get("/drift/model-a", headers=headers_b).status_code == 403
        assert client.get("/retraining/history/model-a", headers=headers_b).status_code == 403
        assert client.get("/audit/model-a", headers=headers_b).status_code == 403

        # 5. User B tries to trigger retraining or rollback User A's model
        assert client.post("/retrain/model-a", json={"drift_score": 0.25, "triggered_by": "manual"}, headers=headers_b).status_code == 403
        assert client.post("/models/model-a/rollback", json={"target_version": "1.0.0"}, headers=headers_b).status_code == 403

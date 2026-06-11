import os
import shutil
import pytest
import joblib
from fastapi.testclient import TestClient
from main import app
from driftguard.tracker import DriftGuard

@pytest.fixture(autouse=True)
def setup_database():
    import os
    import main
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from main import Base

    test_db_url = "sqlite:///test_driftguard_metadata_rollback.db"
    test_engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    
    orig_engine = main.engine
    orig_session = main.SessionLocal
    
    main.engine = test_engine
    main.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    Base.metadata.create_all(bind=test_engine)
    
    yield
    
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()
    if os.path.exists("test_driftguard_metadata_rollback.db"):
        try:
            os.remove("test_driftguard_metadata_rollback.db")
        except Exception:
            pass
            
    main.engine = orig_engine
    main.SessionLocal = orig_session

class DummyModel:
    def __init__(self, name):
        self.name = name
    def predict(self, X):
        return [0.0]

def test_rollback_persistence_and_auto_restoration():
    # Clean artifacts directory
    if os.path.exists("artifacts"):
        shutil.rmtree("artifacts")

    with TestClient(app) as client:
        from unittest.mock import patch
        with patch("httpx.Client") as mock_client_class:
            mock_client_class.return_value.__enter__.return_value = client

            # Register user
            reg = client.post("/users/register", json={"email": "rollback_user@driftguard.com", "name": "Rollback User"})
            api_key = reg.json()["api_key"]
            headers = {"X-API-Key": api_key}

            # Create project
            proj = client.post("/projects", json={"name": "Rollback Project"}, headers=headers).json()
            proj_id = proj["id"]

            # Register model
            client.post("/register", json={
                "model_id": "roll-model",
                "project_id": proj_id,
                "drift_threshold": 0.15,
                "features": ["f1"]
            }, headers=headers)

            # 1. Populate two versions of model artifacts in local storage
            dir_path = f"artifacts/{proj_id}/roll-model"
            os.makedirs(dir_path, exist_ok=True)
            joblib.dump(DummyModel("version_1.0.0_model"), f"{dir_path}/version_1.0.0.pkl")
            joblib.dump(DummyModel("version_1.0.1_model"), f"{dir_path}/version_1.0.1.pkl")

            # Manually seed version registry with 1.0.1 as champion and 1.0.0 as archived
            # This is what a promotion would do, but we simulate it by posting complete or manually updating model metadata
            # Let's mock retraining event and then promote 1.0.1
            retrain_resp = client.post("/retrain/roll-model", json={
                "drift_score": 0.20,
                "triggered_by": "automatic",
                "source": "sdk_callback"
            }, headers=headers)
            event_id = retrain_resp.json()["event_id"]

            complete_resp = client.post("/retrain/roll-model/complete", json={
                "event_id": event_id,
                "validation_passed": True,
                "new_version": "1.0.1",
                "new_accuracy": 0.95,
                "old_accuracy": 0.85
            }, headers=headers)
            assert complete_resp.status_code == 200

            # Current active version is 1.0.1
            model_details = client.get("/models/roll-model", headers=headers).json()
            assert model_details["version"] == "1.0.1"

            # 2. Trigger rollback to 1.0.0
            # The rollback endpoint will load 1.0.0.pkl and restore it, updating the DB version to 1.0.0
            rollback_resp = client.post("/models/roll-model/rollback", json={
                "target_version": "1.0.0"
            }, headers=headers)
            assert rollback_resp.status_code == 200

            # DB state is updated to 1.0.0
            model_details_after = client.get("/models/roll-model", headers=headers).json()
            assert model_details_after["version"] == "1.0.0"

            # 3. Simulate process restart by instantiating a new DriftGuard SDK instance
            # It should automatically fetch active version (1.0.0) from the server
            # and load version_1.0.0.pkl from local storage.
            dg_new = DriftGuard(
                model_id="roll-model",
                api_url="http://localhost:8000",
                api_key=api_key,
                project_id=proj_id
            )

            # Assert that the new client auto-restored the correct model
            assert dg_new._champion_model is not None
            assert dg_new._champion_model.name == "version_1.0.0_model"

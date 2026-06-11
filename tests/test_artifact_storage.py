import os
import shutil
import pytest
import joblib
from fastapi.testclient import TestClient
from main import app
from driftguard.tracker import DriftGuard
from driftguard.callback_runner import RetrainerCallbackRunner

@pytest.fixture(autouse=True)
def setup_database():
    import main
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from main import Base

    test_db_url = "sqlite:///test_driftguard_metadata.db"
    test_engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    
    # Backup original
    orig_engine = main.engine
    orig_session = main.SessionLocal
    
    # Override
    main.engine = test_engine
    main.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    # Recreate tables in test db
    Base.metadata.create_all(bind=test_engine)
    
    yield
    
    # Clean up test database
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()
    if os.path.exists("test_driftguard_metadata.db"):
        try:
            os.remove("test_driftguard_metadata.db")
        except Exception:
            pass
            
    # Restore original
    main.engine = orig_engine
    main.SessionLocal = orig_session

class DummyModel:
    def __init__(self, name, prediction=0.0):
        self.name = name
        self.prediction = prediction
    def predict(self, X):
        return [self.prediction]

def test_model_artifact_persistence_flow():
    # Clean artifacts directory
    if os.path.exists("artifacts"):
        shutil.rmtree("artifacts")

    with TestClient(app) as client:
        from unittest.mock import patch
        with patch("httpx.Client") as mock_client_class:
            mock_client_class.return_value.__enter__.return_value = client

            # Register user
            reg = client.post("/users/register", json={"email": "artifact_user@driftguard.com", "name": "Artifact User"})
            api_key = reg.json()["api_key"]
            headers = {"X-API-Key": api_key}

            # Create project
            proj = client.post("/projects", json={"name": "Artifact Project"}, headers=headers).json()
            proj_id = proj["id"]

            # Register model
            client.post("/register", json={
                "model_id": "art-model",
                "project_id": proj_id,
                "drift_threshold": 0.15,
                "features": ["f1"]
            }, headers=headers)

            # Initialize SDK
            dg = DriftGuard(
                model_id="art-model",
                api_url="http://localhost:8000",
                api_key=api_key,
                project_id=proj_id
            )

            # 1. Set champion model (should trigger joblib dump of 1.0.0)
            champ = DummyModel("champion_model", prediction=1.0)
            dg.set_champion(champ)

            expected_champ_path = f"artifacts/{proj_id}/art-model/version_1.0.0.pkl"
            assert os.path.exists(expected_champ_path)
            loaded_champ = joblib.load(expected_champ_path)
            assert loaded_champ.name == "champion_model"

            # 2. Run retraining callback flow
            # Mock registration of validation data
            dg.set_validation_data([[1.0]], [0])

            @dg.retrainer
            def retrain():
                return DummyModel("challenger_model", prediction=0.0)

            # Mock a running retraining event
            retrain_resp = client.post("/retrain/art-model", json={
                "drift_score": 0.20,
                "triggered_by": "automatic",
                "source": "sdk_callback"
            }, headers=headers)
            assert retrain_resp.status_code == 200

            # Run CallbackRunner manually
            runner = RetrainerCallbackRunner(dg)
            success = runner.run(0.20)
            assert success is True

            # Challenger version should be 1.0.1
            expected_chall_path = f"artifacts/{proj_id}/art-model/version_1.0.1.pkl"
            assert os.path.exists(expected_chall_path)
            loaded_chall = joblib.load(expected_chall_path)
            assert loaded_chall.name == "challenger_model"

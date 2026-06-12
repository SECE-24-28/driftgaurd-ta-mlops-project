import os
import shutil
import pytest
import joblib
import json
import datetime
from zoneinfo import ZoneInfo
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
import main
from main import app, DBModel, DBRetrainingEvent, DBAuditLogEntry, DBUser, DBProject

@pytest.fixture(autouse=True)
def setup_database():
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

    # Clean artifacts
    if os.path.exists("artifacts"):
        shutil.rmtree("artifacts")

class DummyModel:
    def predict(self, X):
        return [0.0]

def test_validation_skip_fails_promotion():
    """
    Validation Skip: Missing validation data must fail promotion,
    no auto-promotion allowed, and write validation_failed audit event.
    """
    import httpx
    from driftguard.tracker import DriftGuard
    from driftguard.callback_runner import RetrainerCallbackRunner

    with TestClient(app) as client:
        with patch("httpx.Client") as mock_client_class:
            mock_client_class.return_value.__enter__.return_value = client
            
            # Register user and project
            reg = client.post("/users/register", json={"email": "val_user@driftguard.com", "name": "Val User"})
            api_key = reg.json()["api_key"]
            headers = {"X-API-Key": api_key}

            proj = client.post("/projects", json={"name": "Val Project"}, headers=headers).json()
            proj_id = proj["id"]

            # Register model
            client.post("/register", json={
                "model_id": "val-model",
                "project_id": proj_id,
                "drift_threshold": 0.15,
                "features": ["f1"]
            }, headers=headers)

            # Initialize SDK tracker without setting validation data
            dg = DriftGuard(
                model_id="val-model",
                api_url="http://localhost:8000",
                api_key=api_key,
                project_id=proj_id
            )

            champ = DummyModel()
            dg.set_champion(champ)

            @dg.retrainer
            def retrain():
                return DummyModel()

            # Trigger retraining event (sdk_callback source)
            retrain_resp = client.post("/retrain/val-model", json={
                "drift_score": 0.20,
                "triggered_by": "automatic",
                "source": "sdk_callback"
            }, headers=headers)
            assert retrain_resp.status_code == 200
            event_id = retrain_resp.json()["event_id"]

            # Run CallbackRunner which should fail since validation data is missing
            runner = RetrainerCallbackRunner(dg)
            success = runner.run(0.20)
            assert success is False

            # Confirm the model status is back to healthy on the server
            model_details = client.get("/models/val-model", headers=headers).json()
            assert model_details["status"] == "healthy"
            assert model_details["version"] == "1.0.0"

            # Check retraining history to confirm it is marked failed
            history_resp = client.get("/retraining/history/val-model", headers=headers).json()
            assert len(history_resp) >= 1
            assert history_resp[0]["status"] == "failed"
            assert "Validation data is missing" in history_resp[0]["details"]["error"]

            # Check audit log to assert validation_failed event was written
            audit_resp = client.get("/audit/val-model", headers=headers).json()
            validation_failed_audits = [a for a in audit_resp if a["event_type"] == "validation_failed"]
            assert len(validation_failed_audits) == 1
            assert "Validation data is missing" in validation_failed_audits[0]["details"]["error"]

def test_retraining_deadlock_recovery():
    """
    Retraining Deadlock: Heartbeat timestamps and watchdog recovery
    auto-mark stale retraining jobs (>5 mins) as failed.
    """
    with TestClient(app) as client:
        # Register user and project
        reg = client.post("/users/register", json={"email": "deadlock@driftguard.com", "name": "Deadlock User"})
        api_key = reg.json()["api_key"]
        headers = {"X-API-Key": api_key}

        proj = client.post("/projects", json={"name": "Project"}, headers=headers).json()
        proj_id = proj["id"]

        # Register model
        client.post("/register", json={
            "model_id": "lock-model",
            "project_id": proj_id,
            "drift_threshold": 0.15,
            "features": ["f1"]
        }, headers=headers)

        # Trigger retraining
        retrain_resp = client.post("/retrain/lock-model", json={
            "drift_score": 0.20,
            "triggered_by": "automatic",
            "source": "sdk_callback"
        }, headers=headers)
        assert retrain_resp.status_code == 200
        event_id = retrain_resp.json()["event_id"]

        # Manually manipulate DB state to simulate a stale retraining job that crashed 10 minutes ago
        db = main.SessionLocal()
        try:
            model = db.query(DBModel).filter(DBModel.model_id == "lock-model", DBModel.project_id == proj_id).first()
            assert model.status == "retraining"

            event = db.query(DBRetrainingEvent).filter(DBRetrainingEvent.id == event_id).first()
            event.last_heartbeat = datetime.datetime.now(ZoneInfo("Asia/Kolkata")) - datetime.timedelta(seconds=350)
            db.commit()
        finally:
            db.close()

        # Query model list to trigger watchdog self-healing recovery helper
        list_resp = client.get("/models", headers=headers)
        assert list_resp.status_code == 200

        # Query model details and confirm status has self-healed back to healthy
        details_resp = client.get("/models/lock-model", headers=headers)
        assert details_resp.json()["status"] == "healthy"

        # Check retraining history to confirm event is marked failed
        history_resp = client.get("/retraining/history/lock-model", headers=headers).json()
        assert history_resp[0]["status"] == "failed"
        assert "timed out" in history_resp[0]["details"]["error"]

def test_namespace_squatting_isolation():
    """
    Namespace Squatting: Enforce composite uniqueness on (project_id, model_id).
    Two users can register the same model_id under their own projects/namespaces.
    """
    with TestClient(app) as client:
        # User 1
        reg1 = client.post("/users/register", json={"email": "u1@driftguard.com", "name": "User 1"})
        key1 = reg1.json()["api_key"]
        headers1 = {"X-API-Key": key1}
        proj1 = client.post("/projects", json={"name": "Proj 1"}, headers=headers1).json()
        proj1_id = proj1["id"]

        # User 2
        reg2 = client.post("/users/register", json={"email": "u2@driftguard.com", "name": "User 2"})
        key2 = reg2.json()["api_key"]
        headers2 = {"X-API-Key": key2}
        proj2 = client.post("/projects", json={"name": "Proj 2"}, headers=headers2).json()
        proj2_id = proj2["id"]

        # Both register the SAME model_id "churn-predictor"
        resp1 = client.post("/register", json={
            "model_id": "churn-predictor",
            "project_id": proj1_id,
            "drift_threshold": 0.35,
            "features": ["feat_a"]
        }, headers=headers1)
        assert resp1.status_code == 200

        resp2 = client.post("/register", json={
            "model_id": "churn-predictor",
            "project_id": proj2_id,
            "drift_threshold": 0.12,
            "features": ["feat_b"]
        }, headers=headers2)
        assert resp2.status_code == 200

        # Verify drift thresholds are isolated
        details1 = client.get("/models/churn-predictor", headers=headers1).json()
        details2 = client.get("/models/churn-predictor", headers=headers2).json()

        assert details1["drift_threshold"] == 0.35
        assert details2["drift_threshold"] == 0.12

def test_rollback_corrupted_artifact_rejection():
    """
    Corrupt Rollback: Verify artifact file exists and loads successfully using joblib.load
    before committing DB changes. Abort transaction on error.
    """
    with TestClient(app) as client:
        # Register user and project
        reg = client.post("/users/register", json={"email": "rollback_check@driftguard.com", "name": "Rollback User"})
        api_key = reg.json()["api_key"]
        headers = {"X-API-Key": api_key}

        proj = client.post("/projects", json={"name": "Proj"}, headers=headers).json()
        proj_id = proj["id"]

        # Register model (creates 1.0.0 champion)
        client.post("/register", json={
            "model_id": "rollback-check",
            "project_id": proj_id,
            "drift_threshold": 0.15,
            "features": ["f1"]
        }, headers=headers)

        # Mock promote to 1.0.1
        retrain_resp = client.post("/retrain/rollback-check", json={
            "drift_score": 0.20,
            "triggered_by": "automatic",
            "source": "sdk_callback"
        }, headers=headers)
        event_id = retrain_resp.json()["event_id"]

        complete_resp = client.post("/retrain/rollback-check/complete", json={
            "event_id": event_id,
            "validation_passed": True,
            "new_version": "1.0.1",
            "new_accuracy": 0.95,
            "old_accuracy": 0.85
        }, headers=headers)
        assert complete_resp.status_code == 200

        # Try to rollback to 1.0.0 (fails with 404 since no artifact file exists yet)
        rollback_resp = client.post("/models/rollback-check/rollback", json={
            "target_version": "1.0.0"
        }, headers=headers)
        assert rollback_resp.status_code == 404
        assert "not found on disk" in rollback_resp.json()["detail"]

        # Current version is still 1.0.1
        model_details = client.get("/models/rollback-check", headers=headers).json()
        assert model_details["version"] == "1.0.1"

        # Now write a corrupted/invalid artifact file
        dir_path = f"artifacts/{proj_id}/rollback-check"
        os.makedirs(dir_path, exist_ok=True)
        with open(f"{dir_path}/version_1.0.0.pkl", "w") as f:
            f.write("corrupted data content that cannot be parsed by joblib")

        # Try to rollback to 1.0.0 (fails with 400 because load throws error)
        rollback_resp_2 = client.post("/models/rollback-check/rollback", json={
            "target_version": "1.0.0"
        }, headers=headers)
        assert rollback_resp_2.status_code == 400
        assert "is corrupted or cannot be loaded" in rollback_resp_2.json()["detail"]

        # Current version remains 1.0.1
        model_details_2 = client.get("/models/rollback-check", headers=headers).json()
        assert model_details_2["version"] == "1.0.1"

def test_dummy_sandbox_simulator_removed():
    """
    Dummy Sandbox Retraining: Remove silent simulation behavior.
    Missing callback/pipeline execution failure must fail retraining.
    No mock accuracy bumps or version bumps.
    """
    # Force mock pipeline failure by raising exception
    with patch("pipeline.retrain_pipeline.run_retraining_flow", side_effect=RuntimeError("Mock Pipeline Failure")):
        with TestClient(app) as client:
            # Register user and project
            reg = client.post("/users/register", json={"email": "sandbox_check@driftguard.com", "name": "Sandbox Check User"})
            api_key = reg.json()["api_key"]
            headers = {"X-API-Key": api_key}

            proj = client.post("/projects", json={"name": "Proj"}, headers=headers).json()
            proj_id = proj["id"]

            # Register model (version 1.0.0, accuracy 0.85)
            client.post("/register", json={
                "model_id": "sim-model",
                "project_id": proj_id,
                "drift_threshold": 0.15,
                "features": ["f1"]
            }, headers=headers)

            # Trigger retraining with source="server" (which runs background task and tries to import pipeline)
            # Since pipeline.retrain_pipeline does not exist or will fail, the server-side pipeline must fail retraining
            retrain_resp = client.post("/retrain/sim-model", json={
                "drift_score": 0.20,
                "triggered_by": "manual",
                "source": "server"
            }, headers=headers)
            assert retrain_resp.status_code == 200
            event_id = retrain_resp.json()["event_id"]

            # Wait briefly for background task to execute
            import time
            time.sleep(1.0)

            # Confirm the model status is back to healthy
            model_details = client.get("/models/sim-model", headers=headers).json()
            assert model_details["status"] == "healthy"
            assert model_details["version"] == "1.0.0"  # Version did not change
            assert model_details["accuracy"] == 0.85     # Accuracy did not bump

            # Confirm retraining event is marked failed
            history_resp = client.get("/retraining/history/sim-model", headers=headers).json()
            assert history_resp[0]["status"] == "failed"
            error_msg = history_resp[0]["details"]["error"]
            assert ("Pipeline flow execution failed" in error_msg) or ("Mock Pipeline Failure" in error_msg)

def test_explicit_model_registration_and_predict_rejection():
    """
    Explicit Model Registration: Verify that unregistered predict requests fail,
    explicit registration works, duplicate registration is rejected, and telemetry works
    after successful registration.
    """
    with TestClient(app) as client:
        # Register user and project
        reg = client.post("/users/register", json={"email": "explicit_reg@driftguard.com", "name": "Explicit Reg User"})
        api_key = reg.json()["api_key"]
        headers = {"X-API-Key": api_key}

        proj = client.post("/projects", json={"name": "Proj"}, headers=headers).json()
        proj_id = proj["id"]

        # 1. Telemetry fails with 404 for unregistered model
        pred_fail = client.post("/predict/unregistered-model", json={
            "features": [1.0, 2.0],
            "prediction": [0.0],
            "drift_score": 0.05
        }, headers=headers)
        assert pred_fail.status_code == 404
        assert "Model must be registered before telemetry." in pred_fail.json()["detail"]

        # 2. Register model explicitly
        reg_resp = client.post("/models/register", json={
            "model_id": "registered-model",
            "project_id": proj_id,
            "drift_threshold": 0.37,
            "accuracy": 0.94,
            "version": "1.0.0",
            "features": ["f1", "f2"]
        }, headers=headers)
        assert reg_resp.status_code == 200

        # 3. Duplicate registration is rejected with 400
        reg_dup = client.post("/models/register", json={
            "model_id": "registered-model",
            "project_id": proj_id,
            "drift_threshold": 0.37,
            "accuracy": 0.94,
            "version": "1.0.0",
            "features": ["f1", "f2"]
        }, headers=headers)
        assert reg_dup.status_code == 400
        assert "Model already registered." in reg_dup.json()["detail"]

        # 4. Telemetry succeeds after registration
        pred_success = client.post("/predict/registered-model", json={
            "features": [1.0, 2.0],
            "prediction": [0.0],
            "drift_score": 0.05
        }, headers=headers)
        assert pred_success.status_code == 200

        # 5. Verify model details contain correct threshold and metadata
        details = client.get("/models/registered-model", headers=headers).json()
        assert details["drift_threshold"] == 0.37
        assert details["accuracy"] == 0.94
        assert details["version"] == "1.0.0"
        assert details["features"] == ["f1", "f2"]

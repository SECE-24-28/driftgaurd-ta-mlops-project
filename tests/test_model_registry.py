import pytest
from main import DBModel, DBModelVersion, DBAuditLogEntry

class DummyModel:
    def predict(self, X):
        return [0.0]

def test_model_registry_flow(client):
    model_id = "registry-test-model"
    
    # 1. Register model (should create initial version 1.0.0 as champion)
    register_resp = client.post("/register", json={
        "model_id": model_id,
        "drift_threshold": 0.15,
        "features": ["feat1", "feat2"]
    })
    assert register_resp.status_code == 200
    assert register_resp.json()["status"] == "registered"
    
    # Get model version history
    history_resp = client.get(f"/models/{model_id}/versions")
    assert history_resp.status_code == 200
    history = history_resp.json()
    assert len(history) == 1
    assert history[0]["version"] == "1.0.0"
    assert history[0]["status"] == "champion"
    assert history[0]["accuracy"] == 0.85

    # 2. Promote version 1.0.1 (via /retrain/{model_id}/complete)
    # Mock a running retraining event first
    retrain_resp = client.post(f"/retrain/{model_id}", json={
        "drift_score": 0.22,
        "triggered_by": "automatic",
        "source": "sdk_callback"
    })
    assert retrain_resp.status_code == 200
    event_id = retrain_resp.json()["event_id"]
    
    # Send complete command to promote 1.0.1
    complete_resp = client.post(f"/retrain/{model_id}/complete", json={
        "event_id": event_id,
        "validation_passed": True,
        "new_version": "1.0.1",
        "new_accuracy": 0.92,
        "old_accuracy": 0.85
    })
    assert complete_resp.status_code == 200
    assert complete_resp.json()["status"] == "promoted"
    
    # Verify version history shows 1.0.1 as champion and 1.0.0 as archived
    history_resp = client.get(f"/models/{model_id}/versions")
    history = history_resp.json()
    assert len(history) == 2
    
    # Order is descending by created_at (1.0.1 first, then 1.0.0)
    assert history[0]["version"] == "1.0.1"
    assert history[0]["status"] == "champion"
    assert history[0]["accuracy"] == 0.92
    
    assert history[1]["version"] == "1.0.0"
    assert history[1]["status"] == "archived"
    assert history[1]["accuracy"] == 0.85
    
    # 3. Test Invalid Rollback to current champion (1.0.1)
    rollback_curr = client.post(f"/models/{model_id}/rollback", json={
        "target_version": "1.0.1"
    })
    assert rollback_curr.status_code == 400
    assert "already the current champion" in rollback_curr.json()["detail"]
    
    # 4. Test Invalid Rollback to non-existent version (1.0.2)
    rollback_nonexist = client.post(f"/models/{model_id}/rollback", json={
        "target_version": "1.0.2"
    })
    assert rollback_nonexist.status_code == 404
    assert "not found in registry" in rollback_nonexist.json()["detail"]

    # 5. Test Successful Rollback to 1.0.0
    import os
    import joblib
    dir_path = f"artifacts/1/{model_id}"
    os.makedirs(dir_path, exist_ok=True)
    joblib.dump(DummyModel(), f"{dir_path}/version_1.0.0.pkl")

    rollback_success = client.post(f"/models/{model_id}/rollback", json={
        "target_version": "1.0.0"
    })
    assert rollback_success.status_code == 200
    assert rollback_success.json()["status"] == "rolled_back"
    assert rollback_success.json()["previous_version"] == "1.0.1"
    assert rollback_success.json()["current_version"] == "1.0.0"
    
    # Verify DBModel has reverted to 1.0.0
    model_details = client.get(f"/models/{model_id}")
    assert model_details.status_code == 200
    assert model_details.json()["version"] == "1.0.0"
    assert model_details.json()["accuracy"] == 0.85
    
    # Verify history now lists 1.0.0 as champion and 1.0.1 as archived
    history_resp = client.get(f"/models/{model_id}/versions")
    history = history_resp.json()
    
    v_100 = next(v for v in history if v["version"] == "1.0.0")
    v_101 = next(v for v in history if v["version"] == "1.0.1")
    assert v_100["status"] == "champion"
    assert v_101["status"] == "archived"
    
    # 6. Verify audit entry was written
    audit_resp = client.get(f"/audit/{model_id}")
    assert audit_resp.status_code == 200
    audits = audit_resp.json()
    # Check if a rollback event exists
    rollback_audits = [a for a in audits if a["event_type"] == "rollback"]
    assert len(rollback_audits) >= 1
    assert rollback_audits[0]["model_version"] == "1.0.0"

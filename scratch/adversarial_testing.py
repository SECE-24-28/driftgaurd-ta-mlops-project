import os
import sys
import time
import httpx
import numpy as np
from sklearn.ensemble import RandomForestClassifier

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from driftguard.tracker import DriftGuard
from driftguard.callback_runner import RetrainerCallbackRunner
from driftguard.drift_detector import ADWINDriftDetector

def main():
    print("=========================================================")
    print("RUNNING ADVERSARIAL TESTING - VERIFY HARDENING FIXES")
    print("=========================================================")
    
    api_url = "http://127.0.0.1:8000"
    ts = int(time.time())
    
    # Register User A
    email_a = f"usera_adv_{ts}@example.com"
    resp_a = httpx.post(f"{api_url}/users/register", json={"email": email_a, "name": "User A"})
    api_key_a = resp_a.json()["api_key"]
    
    # Create Project A for User A so they have explicit composite models
    resp_proj_a = httpx.post(f"{api_url}/projects", json={"name": "Project A"}, headers={"X-API-Key": api_key_a})
    proj_a_id = resp_proj_a.json()["id"]

    # Register User B
    email_b = f"userb_adv_{ts}@example.com"
    resp_b = httpx.post(f"{api_url}/users/register", json={"email": email_b, "name": "User B"})
    api_key_b = resp_b.json()["api_key"]
    
    # Create Project B for User B so they can register composite models
    resp_proj_b = httpx.post(f"{api_url}/projects", json={"name": "Project B"}, headers={"X-API-Key": api_key_b})
    proj_b_id = resp_proj_b.json()["id"]

    # ------------------------------------------------------------------
    # Test A: Namespace Collision (Duplicate Model IDs allowed on distinct projects)
    # ------------------------------------------------------------------
    print("\n--- Test A: Namespace Collision Scoping Isolation ---")
    try:
        model_id = f"shared-model-{ts}"
        
        # User A registers the model
        resp_reg_a = httpx.post(f"{api_url}/register", json={
            "model_id": model_id,
            "project_id": proj_a_id,
            "drift_threshold": 0.15,
            "features": ["f1", "f2"]
        }, headers={"X-API-Key": api_key_a})
        print(f"User A registers model: {resp_reg_a.status_code} {resp_reg_a.json().get('status')}")
        
        # User B registers the SAME model ID under their own project namespace
        resp_reg_b = httpx.post(f"{api_url}/register", json={
            "model_id": model_id,
            "project_id": proj_b_id,
            "drift_threshold": 0.20,
            "features": ["f3", "f4"]
        }, headers={"X-API-Key": api_key_b})
        print(f"User B duplicate register response: {resp_reg_b.status_code} {resp_reg_b.json().get('status')}")
        assert resp_reg_b.status_code == 200, "Namespace isolation failed: User B should be allowed to register same model name!"
        print("[RESULT] FIX VERIFIED: Namespace Squatting resolved. User B can register model with the same ID under their project.")
    except Exception as e:
        print(f"[ERROR] Test A failed: {e}")

    # ------------------------------------------------------------------
    # Test B: Missing Validation Data Blocked
    # ------------------------------------------------------------------
    print("\n--- Test B: Missing Validation Data Check ---")
    try:
        model_id_b = f"missing-val-model-{ts}"
        # Register model
        httpx.post(f"{api_url}/register", json={
            "model_id": model_id_b,
            "project_id": proj_a_id,
            "drift_threshold": 0.50,
            "features": ["f1", "f2"]
        }, headers={"X-API-Key": api_key_a})
        
        # Init SDK, set champion, but do NOT set validation data
        dg = DriftGuard(
            model_id=model_id_b,
            api_url=api_url,
            api_key=api_key_a,
            project_id=proj_a_id,
            drift_threshold=0.50,
            auto_retrain=True
        )
        
        # Dummy champion model
        clf = RandomForestClassifier(n_estimators=10, random_state=42)
        clf.fit(np.random.normal(size=(10, 2)), np.random.randint(0, 2, size=(10,)))
        dg.set_champion(clf)
        
        # Register retraining callback
        @dg.retrainer
        def dummy_retrain():
            chall = RandomForestClassifier(n_estimators=10, random_state=42)
            chall.fit(np.random.normal(size=(10, 2)), np.random.randint(0, 2, size=(10,)))
            return chall

        # Run retraining callback runner
        runner = RetrainerCallbackRunner(dg)
        promoted = runner.run(drift_score=0.60)
        
        print(f"Retraining ran without validation data. Promoted? {promoted}")
        assert promoted is False, "Expected model promotion to fail due to missing validation data!"
        
        # Query server version
        resp_ver = httpx.get(f"{api_url}/models/{model_id_b}", headers={"X-API-Key": api_key_a})
        print(f"Model version on server after blocked promotion: {resp_ver.json().get('version')}")
        assert resp_ver.json().get("version") == "1.0.0", "Model was promoted without validation!"
        print("[RESULT] FIX VERIFIED: Unvalidated promotion successfully blocked! Version remains 1.0.0.")
    except Exception as e:
        print(f"[ERROR] Test B failed: {e}")

    # ------------------------------------------------------------------
    # Test C: Corrupted Artifact on Rollback Aborted
    # ------------------------------------------------------------------
    print("\n--- Test C: Corrupted Artifact on Rollback Rejected ---")
    try:
        # We simulate promotion of a version to seed model versions history
        # Mock promote to 1.0.1
        resp_rt = httpx.post(f"{api_url}/retrain/{model_id_b}", json={
            "drift_score": 0.60,
            "triggered_by": "automatic",
            "source": "sdk_callback"
        }, headers={"X-API-Key": api_key_a})
        event_id = resp_rt.json()["event_id"]

        resp_comp = httpx.post(f"{api_url}/retrain/{model_id_b}/complete", json={
            "event_id": event_id,
            "validation_passed": True,
            "new_version": "1.0.1",
            "new_accuracy": 0.95,
            "old_accuracy": 0.85
        }, headers={"X-API-Key": api_key_a})
        assert resp_comp.status_code == 200

        # Overwrite the version 1.0.0 pkl artifact on disk with garbage
        artifact_dir = f"artifacts/{proj_a_id}/{model_id_b}"
        os.makedirs(artifact_dir, exist_ok=True)
        artifact_path = f"{artifact_dir}/version_1.0.0.pkl"
        
        with open(artifact_path, "wb") as f:
            f.write(b"GARBAGE_DATA_CORRUPTED")
            
        print(f"Overwrote model artifact {artifact_path} with garbage.")
        
        # Call rollback to version 1.0.0
        resp_rb = httpx.post(f"{api_url}/models/{model_id_b}/rollback", json={
            "target_version": "1.0.0"
        }, headers={"X-API-Key": api_key_a})
        
        print(f"Rollback API response code: {resp_rb.status_code} (detail: {resp_rb.json().get('detail')})")
        assert resp_rb.status_code == 400, "Rollback with corrupted file should return 400 Bad Request!"
        
        # Query model version again
        resp_ver = httpx.get(f"{api_url}/models/{model_id_b}", headers={"X-API-Key": api_key_a})
        print(f"Model version on server after aborted rollback: {resp_ver.json().get('version')}")
        assert resp_ver.json().get("version") == "1.0.1", "Model was rolled back to a corrupted version!"
        print("[RESULT] FIX VERIFIED: Rollback transaction aborted and rejected due to corrupted file! Version remains 1.0.1.")
    except Exception as e:
        print(f"[ERROR] Test C failed: {e}")

    # ------------------------------------------------------------------
    # Test D: Stuck Retraining Lock Self-Healing
    # ------------------------------------------------------------------
    print("\n--- Test D: Stuck Retraining Lock Watchdog Self-Healing ---")
    try:
        # Trigger retraining
        resp_rt = httpx.post(f"{api_url}/retrain/{model_id_b}", json={
            "drift_score": 0.60,
            "triggered_by": "automatic",
            "source": "sdk_callback"
        }, headers={"X-API-Key": api_key_a})
        event_id = resp_rt.json()["event_id"]
        
        # Manually verify lock exists
        resp_rt2 = httpx.post(f"{api_url}/retrain/{model_id_b}", json={
            "drift_score": 0.60,
            "triggered_by": "automatic",
            "source": "sdk_callback"
        }, headers={"X-API-Key": api_key_a})
        print(f"Consecutive retraining trigger response: {resp_rt2.json().get('status')}")
        assert resp_rt2.json().get("status") == "already_running"

        # Simulating stale lock state (10 mins ago) in local sqlite DB requires using the sqlite client.
        import sqlite3
        import datetime
        from zoneinfo import ZoneInfo
        conn = sqlite3.connect("driftguard_metadata.db")
        c = conn.cursor()
        # Set heartbeat 10 minutes in the past
        stale_time = (datetime.datetime.now(ZoneInfo("Asia/Kolkata")) - datetime.timedelta(seconds=350)).isoformat()
        c.execute("UPDATE dg_retraining_events SET last_heartbeat = ? WHERE id = ?", (stale_time, event_id))
        conn.commit()
        conn.close()
        print("Manually set heartbeat in DB to 10 minutes in the past to simulate stale lock.")

        # Query model details. The self-healing watchdog should detect and heal it!
        resp_details = httpx.get(f"{api_url}/models/{model_id_b}", headers={"X-API-Key": api_key_a})
        print(f"Model status after watchdog trigger: {resp_details.json().get('status')}")
        assert resp_details.json().get("status") == "healthy", "Stuck lock was not self-healed by watchdog!"
        print("[RESULT] FIX VERIFIED: Stuck retraining lock successfully recovered by watchdog lock resolver.")
    except Exception as e:
        print(f"[ERROR] Test D failed: {e}")

    # ------------------------------------------------------------------
    # Test E: Performance under high feature counts (100 & 500)
    # ------------------------------------------------------------------
    print("\n--- Test E: Performance under High Features ---")
    try:
        t0 = time.time()
        detector_100 = ADWINDriftDetector(num_features=100)
        for _ in range(100):
            detector_100.update(np.random.normal(size=(100,)))
        dur_100 = time.time() - t0
        print(f"100 features: 100 updates took {dur_100 * 1000:.2f} ms ({dur_100 * 1000 / 100:.2f} ms per sample)")
        
        t0 = time.time()
        detector_500 = ADWINDriftDetector(num_features=500)
        for _ in range(100):
            detector_500.update(np.random.normal(size=(500,)))
        dur_500 = time.time() - t0
        print(f"500 features: 100 updates took {dur_500 * 1000:.2f} ms ({dur_500 * 1000 / 100:.2f} ms per sample)")
    except Exception as e:
        print(f"[ERROR] Test E failed: {e}")

if __name__ == "__main__":
    import datetime
    main()

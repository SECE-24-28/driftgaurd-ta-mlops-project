import os
import sys
import time
import subprocess
import httpx
import shutil
import joblib
import numpy as np
from sklearn.tree import DecisionTreeClassifier

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from driftguard.tracker import DriftGuard

def run_test():
    print("=========================================================")
    print("STARTING PHASE 2: ROLLBACK & SERVER RESTART VERIFICATION")
    print("=========================================================")
    
    port = "8099"
    api_url = f"http://127.0.0.1:{port}"
    ts = int(time.time())
    
    # 0. Clean old metadata & artifacts if any
    if os.path.exists("test_rollback_metadata.db"):
        try:
            os.remove("test_rollback_metadata.db")
        except Exception:
            pass

    # Start Uvicorn process on port 8099 with temporary test DB env var
    env = os.environ.copy()
    env["MLFLOW_TRACKING_URI"] = "sqlite:///test_rollback_metadata.db"
    
    print("[Server] Starting isolated Uvicorn server on port 8099...")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", port],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Wait for startup
    time.sleep(4.0)
    
    try:
        # 1. Register User & Project
        print("[Step 1] Registering User and Project...")
        resp_u = httpx.post(f"{api_url}/users/register", json={"email": f"tester_{ts}@rollback.com", "name": "Rollback Tester"})
        if resp_u.status_code != 200:
            print(f"[FAIL] Register User failed: {resp_u.status_code} {resp_u.text}")
            return False
            
        api_key = resp_u.json()["api_key"]
        headers = {"X-API-Key": api_key}
        
        resp_p = httpx.post(f"{api_url}/projects", json={"name": "Rollback Project"}, headers=headers)
        proj_id = resp_p.json()["id"]
        
        # 2. Register Model & Persist v1.0.0 Champion
        print("[Step 2] Registering Model and Persisting v1.0.0 Champion...")
        resp_m = httpx.post(f"{api_url}/register", json={
            "model_id": "test-rollback-model",
            "project_id": proj_id,
            "drift_threshold": 0.15,
            "features": ["f1"]
        }, headers=headers)
        if resp_m.status_code != 200:
            print(f"[FAIL] Model Registration failed: {resp_m.status_code} {resp_m.text}")
            return False
            
        dg = DriftGuard(
            model_id="test-rollback-model",
            api_url=api_url,
            api_key=api_key,
            project_id=proj_id
        )
        
        # Fit model so it has weights
        champ_v1 = DecisionTreeClassifier(max_depth=1)
        champ_v1.fit(np.array([[1.0]]), np.array([1]))
        dg.set_champion(champ_v1)
        
        # Confirm champion v1.0.0 is saved on disk
        champ_path = f"artifacts/{proj_id}/test-rollback-model/version_1.0.0.pkl"
        if not os.path.exists(champ_path):
            print(f"[FAIL] v1.0.0 champion not saved to {champ_path}")
            return False
        print(f"[PASS] v1.0.0 champion saved to {champ_path}")
        
        # 3. Promote v1.0.1 Challenger
        print("[Step 3] Promoting Challenger to v1.0.1...")
        resp_rt = httpx.post(f"{api_url}/retrain/test-rollback-model", json={
            "drift_score": 0.25,
            "triggered_by": "automatic",
            "source": "sdk_callback"
        }, headers=headers)
        event_id = resp_rt.json()["event_id"]
        
        # Save challenger weights manually on disk to simulate local runner persistence
        chall_path = f"artifacts/{proj_id}/test-rollback-model/version_1.0.1.pkl"
        chall_v2 = DecisionTreeClassifier(max_depth=2)
        chall_v2.fit(np.array([[1.0]]), np.array([1]))
        joblib.dump(chall_v2, chall_path)
        
        resp_comp = httpx.post(f"{api_url}/retrain/test-rollback-model/complete", json={
            "event_id": event_id,
            "validation_passed": True,
            "new_version": "1.0.1",
            "new_accuracy": 0.95,
            "old_accuracy": 0.85
        }, headers=headers)
        if resp_comp.status_code != 200:
            print(f"[FAIL] Complete retraining failed: {resp_comp.status_code} {resp_comp.text}")
            return False
            
        # Verify active version is v1.0.1
        resp_det = httpx.get(f"{api_url}/models/test-rollback-model", headers=headers)
        active_ver = resp_det.json()["version"]
        if active_ver != "1.0.1":
            print(f"[FAIL] Active version is {active_ver}, expected 1.0.1")
            return False
        print("[PASS] Challenger promoted to v1.0.1 successfully.")

        # 4. Rollback to v1.0.0
        print("[Step 4] Triggering Rollback to v1.0.0...")
        resp_rb = httpx.post(f"{api_url}/models/test-rollback-model/rollback", json={
            "target_version": "1.0.0"
        }, headers=headers)
        if resp_rb.status_code != 200:
            print(f"[FAIL] Rollback failed: {resp_rb.status_code} {resp_rb.text}")
            return False
            
        # Verify active version is v1.0.0 in DB
        resp_det2 = httpx.get(f"{api_url}/models/test-rollback-model", headers=headers)
        active_ver2 = resp_det2.json()["version"]
        if active_ver2 != "1.0.0":
            print(f"[FAIL] Reverted version in DB is {active_ver2}, expected 1.0.0")
            return False
        print("[PASS] Rollback committed successfully in DB.")
        
        # 5. Restart Uvicorn Server
        print("[Step 5] Simulating Server Restart...")
        server_process.terminate()
        server_process.wait()
        
        # Restart Uvicorn
        server_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", port],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(4.0)
        
        # Verify server is back online
        resp_ver = httpx.get(f"{api_url}/models/test-rollback-model", headers=headers)
        if resp_ver.json()["version"] != "1.0.0":
            print(f"[FAIL] Active version after restart is {resp_ver.json()['version']}, expected 1.0.0")
            return False
            
        # 6. Verify Model Reload
        print("[Step 6] Verifying client side reloading of rolled-back champion...")
        dg_new = DriftGuard(
            model_id="test-rollback-model",
            api_url=api_url,
            api_key=api_key,
            project_id=proj_id
        )
        
        if dg_new._champion_model is None:
            print("[FAIL] Failed to reload model weights (champion_model is None)")
            return False
            
        if dg_new._champion_model.max_depth != 1:
            print(f"[FAIL] Reloaded incorrect model weights: max_depth={dg_new._champion_model.max_depth}, expected 1")
            return False
            
        print("[PASS] Model weights loaded correctly: DecisionTreeClassifier(max_depth=1)")
        print("\n=========================================================")
        print("VERIFICATION RESULT: PASS")
        print("=========================================================")
        return True
        
    finally:
        server_process.terminate()
        server_process.wait()
        
        # Cleanup databases
        if os.path.exists("test_rollback_metadata.db"):
            try:
                os.remove("test_rollback_metadata.db")
            except Exception:
                pass

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)

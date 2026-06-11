import os
import sys
import time
import sqlite3
import httpx
import subprocess
import datetime
import shutil

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def run_test():
    print("=========================================================")
    print("STARTING PHASE 4: CRASH RECOVERY & SELF-HEALING AUDIT")
    print("=========================================================")
    
    port = "8099"
    api_url = f"http://127.0.0.1:{port}"
    ts = int(time.time())
    
    db_file = "driftguard_metadata.db"
    db_bak = "driftguard_metadata.db.bak"
    
    # 0. Backup original database to protect it
    if os.path.exists(db_file):
        shutil.copyfile(db_file, db_bak)
        print(f"[Backup] Backed up {db_file} to {db_bak}")
    else:
        db_bak = None

    # Start isolated server
    env = os.environ.copy()
    
    print("[Server] Starting isolated Uvicorn server...")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", port],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(4.0)
    
    try:
        # 1. Register User & Model
        print("[Step 1] Registering User, Project, and Model...")
        resp_u = httpx.post(f"{api_url}/users/register", json={"email": f"crasher_{ts}@driftguard.com", "name": "Crash Tester"})
        if resp_u.status_code != 200:
            print(f"[FAIL] Register User failed: {resp_u.status_code} {resp_u.text}")
            return False
        api_key = resp_u.json()["api_key"]
        headers = {"X-API-Key": api_key}
        
        resp_p = httpx.post(f"{api_url}/projects", json={"name": "Crash Project"}, headers=headers)
        proj_id = resp_p.json()["id"]
        
        httpx.post(f"{api_url}/register", json={
            "model_id": f"crash-model-{ts}",
            "project_id": proj_id,
            "drift_threshold": 0.15,
            "features": ["f1"]
        }, headers=headers)
        
        # 2. Trigger Retraining to Lock the Model (Status -> 'retraining')
        print("[Step 2] Locking model by starting retraining...")
        resp_rt = httpx.post(f"{api_url}/retrain/crash-model-{ts}", json={
            "drift_score": 0.25,
            "triggered_by": "automatic",
            "source": "sdk_callback"
        }, headers=headers)
        event_id = resp_rt.json()["event_id"]
        
        # Verify status is 'retraining'
        resp_det = httpx.get(f"{api_url}/models/crash-model-{ts}", headers=headers)
        assert resp_det.json()["status"] == "retraining", "Model status should be locked in 'retraining'"
        print("[PASS] Model locked in 'retraining' state.")
        
        # 3. Simulate Server Crash by terminating the server
        print("[Step 3] Simulating server crash during retraining (killing server)...")
        server_process.terminate()
        server_process.wait()
        
        # 4. Modify heartbeat in SQLite to represent a stale lock from 10 minutes ago
        print("[Step 4] Modifying SQLite DB to set a stale retraining heartbeat from 10 minutes ago...")
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        stale_time = (datetime.datetime.utcnow() - datetime.timedelta(seconds=400)).strftime('%Y-%m-%d %H:%M:%S.%f')
        c.execute("UPDATE dg_retraining_events SET last_heartbeat = ? WHERE id = ?", (stale_time, event_id))
        conn.commit()
        conn.close()
        
        # 5. Restart Uvicorn Server
        print("[Step 5] Restarting Uvicorn server...")
        server_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", port],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        time.sleep(4.0)
        
        # 6. Query Model Details to Trigger Watchdog Healing
        print("[Step 6] Querying model details to trigger self-healing watchdog...")
        resp_healed = httpx.get(f"{api_url}/models/crash-model-{ts}", headers=headers)
        if resp_healed.status_code != 200:
            print(f"[FAIL] Query healed model returned: {resp_healed.status_code}")
            return False
            
        status_after = resp_healed.json()["status"]
        print(f"Model status after watchdog trigger: '{status_after}'")
        
        if status_after != "healthy":
            print(f"[FAIL] Expected model status to be healed to 'healthy', got '{status_after}'")
            return False
            
        print("[PASS] Watchdog successfully self-healed the retraining deadlock!")
        
        # 7. Check retraining history event status
        resp_hist = httpx.get(f"{api_url}/retraining/history/crash-model-{ts}", headers=headers)
        event_status = resp_hist.json()[0]["status"]
        print(f"Retraining event status: '{event_status}'")
        if event_status != "failed":
            print(f"[FAIL] Expected retraining event status to be updated to 'failed', got '{event_status}'")
            return False
        print("[PASS] Retraining event state updated to 'failed'.")
        
        print("\n=========================================================")
        print("CRASH RECOVERY VERIFICATION RESULT: PASS")
        print("=========================================================")
        return True

    finally:
        server_process.terminate()
        server_process.wait()
        
        # Restore backup database
        if db_bak and os.path.exists(db_bak):
            try:
                os.remove(db_file)
            except Exception:
                pass
            shutil.copyfile(db_bak, db_file)
            os.remove(db_bak)
            print(f"[Restore] Restored original {db_file} from {db_bak}")

if __name__ == "__main__":
    success = run_test()
    sys.exit(0 if success else 1)

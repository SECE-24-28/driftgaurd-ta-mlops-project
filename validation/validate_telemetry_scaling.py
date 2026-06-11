import os
import sys
import time
import sqlite3
import httpx
import subprocess
import threading
import numpy as np
from sklearn.tree import DecisionTreeClassifier

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from driftguard.tracker import DriftGuard

def get_thread_count():
    try:
        import psutil
        return psutil.Process(os.getpid()).num_threads()
    except ImportError:
        return threading.active_count()

def get_memory_mb():
    try:
        import psutil
        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except ImportError:
        return 0.0

def main():
    print("=========================================================")
    print("PHASE 5: TELEMETRY SCALING & RELIABILITY VALIDATION")
    print("=========================================================")
    
    port = "8095"
    api_url = f"http://127.0.0.1:{port}"
    db_file = "driftguard_metadata.db"
    ts = int(time.time())
    dg = None
    
    # Start isolated FastAPI server
    env = os.environ.copy()
    
    print("[Server] Starting isolated Uvicorn server on port 8095...")
    server_log = open("uvicorn_scaling_server.log", "w", encoding="utf-8", buffering=1)
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", port],
        env=env,
        stdout=server_log,
        stderr=server_log
    )
    
    # Wait for server startup
    time.sleep(4.0)
    
    try:
        # 1. Register User & Project
        print("[Step 1] Registering User & Project...")
        resp_u = httpx.post(f"{api_url}/users/register", json={"email": f"scaler_{ts}@driftguard.com", "name": "Scale Tester"})
        if resp_u.status_code != 200:
            print(f"[FAIL] User registration failed: {resp_u.text}")
            sys.exit(1)
            
        api_key = resp_u.json()["api_key"]
        headers = {"X-API-Key": api_key}
        
        resp_p = httpx.post(f"{api_url}/projects", json={"name": "Scaling Project"}, headers=headers)
        proj_id = resp_p.json()["id"]
        
        # 2. Pre-register model
        print("[Step 2] Registering model...")
        model_id = f"scale-test-model-{ts}"
        resp_m = httpx.post(f"{api_url}/register", json={
            "model_id": model_id,
            "project_id": proj_id,
            "drift_threshold": 0.50,
            "features": ["f1"]
        }, headers=headers)
        if resp_m.status_code != 200:
            print(f"[FAIL] Model registration failed: {resp_m.text}")
            sys.exit(1)
            
        # 3. Setup SDK Client
        print("[Step 3] Initializing DriftGuard SDK Client...")
        dg = DriftGuard(
            model_id=model_id,
            api_url=api_url,
            api_key=api_key,
            project_id=proj_id,
            drift_threshold=0.50,
            auto_retrain=False
        )
        
        clf = DecisionTreeClassifier(max_depth=1)
        clf.fit(np.array([[1.0]]), np.array([1]))
        wrapped = dg.wrap(clf)
        
        # 4. Stream 10,000 predictions rapidly
        print("[Step 4] Streaming 10,000 predictions rapidly...")
        initial_threads = get_thread_count()
        initial_mem = get_memory_mb()
        
        max_threads_observed = initial_threads
        start_time = time.time()
        
        for i in range(10000):
            # Run inference
            _ = wrapped.predict(np.array([[1.0]]))
            
            # Periodically sample thread count
            if i % 500 == 0:
                t_count = get_thread_count()
                if t_count > max_threads_observed:
                    max_threads_observed = t_count
                    
        duration = time.time() - start_time
        print(f"Prediction loop completed. 10,000 predicts took {duration:.2f} seconds.")
        
        # Wait for queue to drain
        print("Waiting for telemetry queue to drain...")
        drain_start = time.time()
        while not dg._telemetry_queue.empty():
            time.sleep(0.5)
            # Sample threads and queues
            t_count = get_thread_count()
            if t_count > max_threads_observed:
                max_threads_observed = t_count
            if time.time() - drain_start > 200.0:
                print("[WARNING] Telemetry queue drain timed out after 200s.")
                break
                
        # Wait a small buffer for last HTTP request thread completion
        time.sleep(2.0)
        
        final_threads = get_thread_count()
        final_mem = get_memory_mb()
        
        print("\n--- MEASURED METRICS ---")
        print(f"Initial SDK Threads  : {initial_threads}")
        print(f"Max Threads Observed : {max_threads_observed}")
        print(f"Final SDK Threads    : {final_threads}")
        print(f"Initial Memory       : {initial_mem:.2f} MB")
        print(f"Final Memory         : {final_mem:.2f} MB")
        print(f"Memory Growth        : {final_mem - initial_mem:.2f} MB")
        
        # 5. Verify database count
        conn = sqlite3.connect(db_file)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM dg_predictions WHERE model_id = ?", (model_id,))
        db_count = c.fetchone()[0]
        conn.close()
        
        print(f"Logged Telemetry Count in DB : {db_count} / 10000")
        
        # Check server health
        resp_h = httpx.get(f"{api_url}/api/health")
        server_ok = resp_h.status_code == 200
        print(f"FastAPI Server Health Status : {'HEALTHY' if server_ok else 'CRASHED'}")
        
        # 6. Evaluation Criteria
        # Previous architecture would spawn 10,000 threads.
        # Hardened architecture should only spawn 1 dedicated background thread.
        # Allow a buffer of a few threads for other internal processes.
        thread_explosion = max_threads_observed > (initial_threads + 5)
        
        pass_test = (
            not thread_explosion and
            db_count >= 9990 and 
            server_ok
        )
        
        print("\n=========================================================")
        if pass_test:
            print("TELEMETRY SCALING TEST RESULT: PASS")
            print("=========================================================")
            sys.exit(0)
        else:
            print("TELEMETRY SCALING TEST RESULT: FAIL")
            if thread_explosion:
                print(f" - Reason: Thread explosion detected! Max threads observed: {max_threads_observed}")
            if db_count == 0:
                print(" - Reason: No telemetry logs found in DB.")
            if not server_ok:
                print(" - Reason: FastAPI server crashed or is unreachable.")
            print("=========================================================")
            sys.exit(1)
            
    finally:
        if dg is not None:
            try:
                dg.shutdown()
            except Exception as e:
                print(f"Error shutting down DriftGuard: {e}")
        server_process.terminate()
        server_process.wait()
        try:
            server_log.close()
        except:
            pass

if __name__ == "__main__":
    main()

import subprocess
import time
import sys
import os
import httpx
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import make_classification

# Configure ports and temporary db
TEST_PORT = 8099
API_URL = f"http://127.0.0.1:{TEST_PORT}"
MODEL_ID = "telemetry-test-model"

# Set environment variables for the test run to isolate from production / Docker env
os.environ["DRIFTGUARD_API_URL"] = API_URL
os.environ["DRIFTGUARD_DRIFT_THRESHOLD"] = "0.5"
os.environ["MLFLOW_TRACKING_URI"] = "sqlite:///test_mlflow.db"

def start_server():
    print(f"[*] Starting local DriftGuard API server on port {TEST_PORT}...")
    # Use SQLite for the test to avoid docker dependencies
    env = os.environ.copy()
    env["POSTGRES_DB"] = ""  # Clear PG env to force SQLite fallback in main.py
    env["POSTGRES_HOST"] = ""
    
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", f"--port={TEST_PORT}", "--host=127.0.0.1"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )
    
    # Wait for server to be healthy
    max_retries = 10
    for i in range(max_retries):
        try:
            resp = httpx.get(f"{API_URL}/api/health", timeout=1.0)
            if resp.status_code == 200:
                print("[+] Server started successfully and is healthy.")
                return server_process
        except Exception:
            pass
        time.sleep(0.5)
        
    # If failed to start, print server logs
    stdout, stderr = server_process.communicate(timeout=1.0)
    print("[-] Failed to start server.", file=sys.stderr)
    print("STDOUT:", stdout, file=sys.stderr)
    print("STDERR:", stderr, file=sys.stderr)
    server_process.kill()
    sys.exit(1)

def run_telemetry_audit(server_process):
    try:
        # 1. SDK import & setup
        print("\n[*] Initializing DriftGuard SDK...")
        from driftguard import DriftGuard
        
        X, y = make_classification(n_samples=100, n_features=3, n_redundant=0, random_state=42)
        model = RandomForestClassifier(n_estimators=10)
        model.fit(X, y)
        
        dg = DriftGuard(
            model_id=MODEL_ID,
            api_url=API_URL,
            drift_threshold=0.5
        )
        dg.set_champion(model)
        dg.set_validation_data(X[:10], y[:10])
        
        wrapped = dg.wrap(model)
        
        # 2. Make prediction and intercept telemetry
        test_features = [[1.5, 2.5, -0.5]]
        print(f"[*] Executing wrapped.predict(X) with features: {test_features}")
        prediction = wrapped.predict(test_features)
        print(f"[+] Prediction finished. Value: {prediction}")
        
        # Wait a short moment for the async thread to execute httpx POST
        print("[*] Waiting for asynchronous telemetry thread to complete POST...")
        time.sleep(1.5)
        
        # 3. Query drift endpoint to check backend persistence
        drift_url = f"{API_URL}/drift/{MODEL_ID}"
        print(f"[*] Querying GET {drift_url} to fetch stored telemetry...")
        
        resp = httpx.get(drift_url, timeout=3.0)
        if resp.status_code != 200:
            print(f"[-] GET /drift/{MODEL_ID} failed with status {resp.status_code}", file=sys.stderr)
            sys.exit(1)
            
        logs = resp.json()
        print(f"[+] Endpoint returned {len(logs)} records.")
        
        if not logs:
            print("[-] Failure: Telemetry list is empty. Stored telemetry was not returned.", file=sys.stderr)
            sys.exit(1)
            
        # Match latest record
        latest_log = logs[-1] # The API returns logs reversed/chronological order
        print(f"[+] Stored telemetry record found:")
        print(f"    Timestamp:   {latest_log.get('timestamp')}")
        print(f"    Features:    {latest_log.get('features')}")
        print(f"    Prediction:  {latest_log.get('prediction')}")
        print(f"    Drift Score: {latest_log.get('drift_score')}")
        
        # Validation checks
        stored_features = latest_log.get('features')
        stored_prediction = latest_log.get('prediction')
        
        assert np.allclose(stored_features, test_features[0]), f"Features mismatch: {stored_features} vs {test_features[0]}"
        assert np.allclose(stored_prediction, prediction[0]), f"Prediction mismatch: {stored_prediction} vs {prediction[0]}"
        
        print("\n==================================================")
        print("SUCCESS: Telemetry was successfully sent, routed, and persisted.")
        print("==================================================")
        
    except Exception as e:
        print(f"\n[-] Audit failed with error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    finally:
        print("[*] Shutting down DriftGuard local server...")
        server_process.terminate()
        server_process.wait()
        
        # Clean up SQLite db if created locally
        if os.path.exists("driftguard_metadata.db"):
            try:
                os.remove("driftguard_metadata.db")
                print("[*] Cleaned up temporary database: driftguard_metadata.db")
            except Exception:
                pass
        if os.path.exists("test_mlflow.db"):
            try:
                os.remove("test_mlflow.db")
                print("[*] Cleaned up temporary database: test_mlflow.db")
            except Exception:
                pass

if __name__ == "__main__":
    server = start_server()
    run_telemetry_audit(server)

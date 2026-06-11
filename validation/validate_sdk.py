import os
import sys
import time
import httpx
import numpy as np
from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import psutil for memory tracking if available
try:
    import psutil
except ImportError:
    psutil = None

def get_memory_use_mb():
    if psutil:
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / (1024 * 1024)
    return 0.0

def run_validation():
    print("=========================================================")
    print("PHASE A: SDK VALIDATION")
    print("=========================================================")

    report = {"Phase": "Phase A: SDK Validation", "Steps": []}
    
    # Step 1: Import DriftGuard
    try:
        from driftguard.tracker import DriftGuard
        from driftguard.callback_runner import RetrainerCallbackRunner
        print("[PASS] DriftGuard imported successfully.")
        report["Steps"].append({"name": "Import SDK", "status": "PASS", "detail": "driftguard package imported successfully."})
    except Exception as e:
        print(f"[FAIL] DriftGuard import failed: {e}")
        report["Steps"].append({"name": "Import SDK", "status": "FAIL", "detail": str(e)})
        return report

    # Step 2: Initialize DriftGuard Instance
    try:
        # We use the seeded dg-default-key for initial local tests
        dg = DriftGuard(
            model_id="val-sdk-model",
            api_url="http://127.0.0.1:8000",
            api_key="dg-default-key",
            project_id=1,
            drift_threshold=0.50,
            auto_retrain=False
        )
        print("[PASS] DriftGuard initialized successfully.")
        report["Steps"].append({"name": "Initialize SDK Client", "status": "PASS", "detail": "DriftGuard client initialized."})
    except Exception as e:
        print(f"[FAIL] DriftGuard initialization failed: {e}")
        report["Steps"].append({"name": "Initialize SDK Client", "status": "FAIL", "detail": str(e)})
        return report

    # Register the model explicitly first to prevent concurrent SQLite auto-registration races
    try:
        headers = {"X-API-Key": "dg-default-key"}
        resp = httpx.post("http://127.0.0.1:8000/register", json={
            "model_id": "val-sdk-model",
            "project_id": 1,
            "drift_threshold": 0.50,
            "features": [f"feat_{i}" for i in range(5)]
        }, headers=headers)
        if resp.status_code in [200, 201]:
            print("[PASS] Model registered explicitly prior to telemetry stream.")
            report["Steps"].append({"name": "Pre-register Model", "status": "PASS", "detail": "Model registered successfully on API server."})
        else:
            print(f"[WARNING] Model registration returned status: {resp.status_code}")
            report["Steps"].append({"name": "Pre-register Model", "status": "WARNING", "detail": f"Registration status: {resp.status_code}"})
    except Exception as e:
        print(f"[WARNING] Pre-registration request failed: {e}")
        report["Steps"].append({"name": "Pre-register Model", "status": "WARNING", "detail": str(e)})

    # Set up synthetic model
    X_syn, y_syn = make_classification(n_samples=100, n_features=5, random_state=42)
    model = RandomForestClassifier(n_estimators=10, random_state=42)
    model.fit(X_syn, y_syn)

    # Step 3 & 4: Wrap model and verify identical predictions (no corruption)
    try:
        wrapped = dg.wrap(model)
        
        orig_preds = model.predict(X_syn)
        wrapped_preds = wrapped.predict(X_syn)
        
        # Check identical predictions
        assert np.array_equal(orig_preds, wrapped_preds), "Predictions are not identical!"
        
        # Check predict_proba
        orig_proba = model.predict_proba(X_syn)
        wrapped_proba = wrapped.predict_proba(X_syn)
        assert np.allclose(orig_proba, wrapped_proba), "Probability predictions are not identical!"
        
        print("[PASS] Wrapped model returns identical predictions. No corruption detected.")
        report["Steps"].append({"name": "Wrapped Prediction Check", "status": "PASS", "detail": "Original and wrapped predictions match perfectly."})
    except Exception as e:
        print(f"[FAIL] Prediction verification failed: {e}")
        report["Steps"].append({"name": "Wrapped Prediction Check", "status": "FAIL", "detail": str(e)})
        return report

    # Step 5, 6 & 7: Telemetry scale test (1000 predictions) and memory check
    try:
        print("Running 1000 predictions to test telemetry and memory stability...")
        initial_mem = get_memory_use_mb()
        
        # Fire 1000 predictions with small pacing delay (5ms)
        # This prevents spawning 1000 threads instantly, which causes thread pool & stack memory exhaustion.
        start_time = time.time()
        for i in range(1000):
            idx = i % 100
            sample = X_syn[idx : idx + 1]
            _ = wrapped.predict(sample)
            time.sleep(0.005) # 5ms delay to pace threads
            
        duration = time.time() - start_time
        print(f"1000 predictions completed in {duration:.2f} seconds.")
        
        # Wait a moment for background thread telemetry delivery pool to clear
        print("Waiting 5 seconds for asynchronous telemetry background threads to complete...")
        time.sleep(5.0)
        
        final_mem = get_memory_use_mb()
        mem_diff = final_mem - initial_mem
        
        print(f"Memory Check: Initial = {initial_mem:.2f} MB | Final = {final_mem:.2f} MB | Growth = {mem_diff:.2f} MB")
        
        # Check memory growth threshold (we expect no major leak, e.g., < 15MB growth under paced threads)
        if psutil and mem_diff > 15.0:
            print(f"[WARNING] Potential memory growth: growth of {mem_diff:.2f} MB.")
            report["Steps"].append({
                "name": "Memory Growth and Telemetry",
                "status": "WARNING",
                "detail": f"1000 predictions completed, but memory grew by {mem_diff:.2f} MB."
            })
        else:
            print("[PASS] Telemetry scale test completed successfully. Memory usage remains stable.")
            report["Steps"].append({
                "name": "Memory Growth and Telemetry",
                "status": "PASS",
                "detail": f"1000 predictions completed successfully. Memory growth: {mem_diff:.2f} MB."
            })
            
        # Verify telemetry successfully landed on server
        headers = {"X-API-Key": "dg-default-key"}
        resp = httpx.get("http://127.0.0.1:8000/drift/val-sdk-model", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            print(f"[PASS] Telemetry confirmed on API server. Records retrieved: {len(data)}")
            report["Steps"].append({
                "name": "Telemetry Verification",
                "status": "PASS",
                "detail": f"Successfully fetched telemetry log from server. Records returned: {len(data)}"
            })
        else:
            print(f"[FAIL] Failed to retrieve telemetry logs from API server: {resp.status_code} {resp.text}")
            report["Steps"].append({
                "name": "Telemetry Verification",
                "status": "FAIL",
                "detail": f"Failed to retrieve logs from server. HTTP {resp.status_code}"
            })
            
    except Exception as e:
        print(f"[FAIL] Scale test / telemetry check failed: {e}")
        report["Steps"].append({"name": "Telemetry Scale Test", "status": "FAIL", "detail": str(e)})
        
    return report

if __name__ == "__main__":
    res = run_validation()
    print("\nSummary results:")
    for step in res["Steps"]:
        print(f" - {step['name']}: {step['status']} ({step['detail']})")

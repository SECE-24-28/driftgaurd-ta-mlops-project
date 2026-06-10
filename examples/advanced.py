import os
import sys
import time
import numpy as np
import httpx
from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier

# Ensure workspace root is in python path for local execution in the repo
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from driftguard import DriftGuard

# 1. Create synthetic datasets (training and validation)
X_train, y_train = make_classification(n_samples=200, n_features=5, random_state=42)
X_val, y_val = make_classification(n_samples=50, n_features=5, random_state=43)

# 2. Train baseline Champion model
champion = RandomForestClassifier(n_estimators=10, max_depth=3, random_state=42)
champion.fit(X_train, y_train)

# 3. Initialize DriftGuard (defaults to API URL http://localhost:8000)
model_id = "advanced-fraud-detector"
dg = DriftGuard(
    model_id=model_id,
    drift_threshold=0.15,
    auto_retrain=True
)

# Register champion and validation data for automated challenge validation
dg.set_champion(champion)
dg.set_validation_data(X_val, y_val)

# 4. Define the local retrainer callback using the @dg.retrainer decorator
@dg.retrainer
def retrain_callback():
    print("\n[Retrainer] Callback triggered! Retraining model...")
    # Train a new challenger model that beats the champion
    challenger = RandomForestClassifier(n_estimators=50, max_depth=5, random_state=100)
    challenger.fit(X_train, y_train)
    print("[Retrainer] Retraining completed successfully. Returning challenger model.")
    return challenger

def main():
    print("--- DriftGuard Advanced Example ---")
    
    # Check if DriftGuard API is running
    api_running = False
    try:
        resp = httpx.get(f"{dg.api_url}/api/health", timeout=2.0)
        if resp.status_code == 200:
            api_running = True
            print("DriftGuard API Gateway is online.")
    except Exception:
        print("DriftGuard API Gateway is offline. Telemetry will run in local-only/fallback mode.")

    # Wrap the champion model
    wrapped = dg.wrap(champion)
    
    # 5. Simulate normal predictions (under threshold)
    print("\n--- Phase 1: Normal Predictions ---")
    for _ in range(5):
        normal_input = np.random.normal(0.0, 1.0, (1, 5))
        wrapped.predict(normal_input)
    
    # 6. Simulate drift (inject out-of-distribution inputs to trigger retraining)
    print("\n--- Phase 2: Simulating Concept Drift ---")
    for i in range(12):
        # High drift values shift the mean to trigger threshold breach
        drifted_input = np.random.normal(15.0, 1.0, (1, 5))
        wrapped.predict(drifted_input)
        time.sleep(0.1)
        
    # Wait for the retrainer callback thread to finish
    time.sleep(3.0)

    # 7. Query version history and perform rollback (if API is online)
    if api_running:
        print("\n--- Phase 3: Model Registry & Rollback ---")
        # Get version history
        versions_url = f"{dg.api_url}/models/{model_id}/versions"
        versions_resp = httpx.get(versions_url)
        print(f"Version History:\n{versions_resp.json()}")

        # Rollback to the initial champion (1.0.0)
        rollback_url = f"{dg.api_url}/models/{model_id}/rollback"
        rollback_resp = httpx.post(rollback_url, json={"target_version": "1.0.0"})
        if rollback_resp.status_code == 200:
            print("Successfully rolled back to version 1.0.0!")
            print(rollback_resp.json())
        else:
            print(f"Rollback failed: {rollback_resp.json()}")
    else:
        print("\n--- Phase 3: Model Registry & Rollback (Skipped) ---")
        print("Start the FastAPI server (main.py) to enable version history and rollback endpoints.")

if __name__ == "__main__":
    main()

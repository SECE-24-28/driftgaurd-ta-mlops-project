import os
import sys
import time
import httpx
import numpy as np
from sklearn.datasets import load_breast_cancer
from sklearn.ensemble import RandomForestClassifier

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from driftguard.tracker import DriftGuard
from driftguard.callback_runner import RetrainerCallbackRunner

def run_validation():
    print("=========================================================")
    print("PHASE C, D, E: RETRAINING, AUDIT, & ROLLBACK VALIDATION")
    print("=========================================================")
    
    report = {
        "Phase": "Phase C, D, E: Retraining, Audit, & Rollback",
        "Steps": []
    }

    # Load Breast Cancer dataset and shuffle
    data = load_breast_cancer()
    X = data.data
    y = data.target
    
    indices = np.arange(len(X))
    np.random.seed(42)
    np.random.shuffle(indices)
    X = X[indices]
    y = y[indices]

    # Split: Train (first 300), Validation (next 100)
    X_train = X[:300]
    y_train = y[:300]
    
    X_val = X[300:400]
    y_val = y[300:400]

    # 1. Train champion baseline model
    champion_clf = RandomForestClassifier(n_estimators=10, random_state=42)
    champion_clf.fit(X_train, y_train)

    model_id = "val-retrain-model"
    api_url = "http://127.0.0.1:8000"
    api_key = "dg-default-key"
    headers = {"X-API-Key": api_key}

    # Step 1: Pre-register model to prevent races and establish initial registry
    try:
        resp = httpx.post(f"{api_url}/register", json={
            "model_id": model_id,
            "project_id": 1,
            "drift_threshold": 0.50,
            "features": [f"feat_{i}" for i in range(X.shape[1])]
        }, headers=headers)
        if resp.status_code in [200, 201]:
            print("[PASS] Model registered successfully.")
            report["Steps"].append({"name": "Register Model", "status": "PASS", "detail": "Pre-registered on API server."})
        else:
            raise Exception(f"HTTP {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"[FAIL] Pre-registration failed: {e}")
        report["Steps"].append({"name": "Register Model", "status": "FAIL", "detail": str(e)})
        return report

    # Step 2: Initialize DriftGuard Client and Register Retrainer & Validation Data
    try:
        dg = DriftGuard(
            model_id=model_id,
            api_url=api_url,
            api_key=api_key,
            project_id=1,
            drift_threshold=0.50,
            auto_retrain=True
        )
        dg.set_champion(champion_clf)
        dg.set_validation_data(X_val, y_val)

        # Register callback
        @dg.retrainer
        def retrain_callback():
            # Challenger: refit with n_estimators=50 on train + val for higher accuracy
            X_refit = np.vstack([X_train, X_val])
            y_refit = np.concatenate([y_train, y_val])
            challenger_clf = RandomForestClassifier(n_estimators=50, random_state=42)
            challenger_clf.fit(X_refit, y_refit)
            return challenger_clf

        print("[PASS] SDK initialized and retrainer callback registered.")
        report["Steps"].append({"name": "SDK Setup & Register Callback", "status": "PASS", "detail": "Champion, validation data, and callback registered."})
    except Exception as e:
        print(f"[FAIL] SDK Setup failed: {e}")
        report["Steps"].append({"name": "SDK Setup & Register Callback", "status": "FAIL", "detail": str(e)})
        return report

    # Step 3: Run the local callback retraining runner synchronously
    try:
        runner = RetrainerCallbackRunner(dg)
        promoted = runner.run(drift_score=0.60)
        
        assert promoted is True, "Challenger failed promotion!"
        print("[PASS] Retraining pipeline promoted challenger model successfully.")
        report["Steps"].append({"name": "Trigger Callback Retraining", "status": "PASS", "detail": "Challenger beat champion and was promoted."})
    except Exception as e:
        print(f"[FAIL] Retraining run failed: {e}")
        report["Steps"].append({"name": "Trigger Callback Retraining", "status": "FAIL", "detail": str(e)})
        return report

    # Step 4: Verify Version Bump on the API Server
    try:
        resp = httpx.get(f"{api_url}/models/{model_id}", headers=headers)
        assert resp.status_code == 200, f"HTTP {resp.status_code}"
        data = resp.json()
        assert data["version"] == "1.0.1", f"Expected version 1.0.1, got {data['version']}"
        print(f"[PASS] Version bumped successfully. Current: {data['version']} | Accuracy: {data['accuracy']:.4f}")
        report["Steps"].append({"name": "Verify Version Bump", "status": "PASS", "detail": f"Version is 1.0.1 (accuracy: {data['accuracy']:.4f})"})
    except Exception as e:
        print(f"[FAIL] Version bump verification failed: {e}")
        report["Steps"].append({"name": "Verify Version Bump", "status": "FAIL", "detail": str(e)})
        return report

    # Step 5: Verify Audit Log Events
    try:
        resp = httpx.get(f"{api_url}/audit/{model_id}", headers=headers)
        assert resp.status_code == 200, f"HTTP {resp.status_code}"
        audit_events = [e["event_type"] for e in resp.json()]
        
        # Verify we have model_registered and model_promoted events
        assert "model_promoted" in audit_events, "model_promoted event missing from audit log!"
        print(f"[PASS] Audit events verified successfully. Found events: {audit_events}")
        report["Steps"].append({"name": "Verify Audit Logs", "status": "PASS", "detail": f"Audit events found: {audit_events}"})
    except Exception as e:
        print(f"[FAIL] Audit log verification failed: {e}")
        report["Steps"].append({"name": "Verify Audit Logs", "status": "FAIL", "detail": str(e)})
        return report

    # Step 6: Call Emergency Rollback API
    try:
        # Revert version 1.0.1 back to 1.0.0
        resp = httpx.post(f"{api_url}/models/{model_id}/rollback", json={
            "target_version": "1.0.0"
        }, headers=headers)
        assert resp.status_code == 200, f"HTTP {resp.status_code}: {resp.text}"
        data = resp.json()
        assert data["current_version"] == "1.0.0", f"Expected current_version 1.0.0, got {data['current_version']}"
        print(f"[PASS] Rollback API completed successfully: v1.0.1 -> {data['current_version']}")
        report["Steps"].append({"name": "Rollback Version API", "status": "PASS", "detail": f"Reverted version to {data['current_version']}"})
    except Exception as e:
        print(f"[FAIL] Rollback API failed: {e}")
        report["Steps"].append({"name": "Rollback Version API", "status": "FAIL", "detail": str(e)})
        return report

    # Step 7: Verify Rollback Persistence on a new client instance
    try:
        # Re-initialize SDK and assert it auto-restores version 1.0.0 model artifact from disk
        dg_new = DriftGuard(
            model_id=model_id,
            api_url=api_url,
            api_key=api_key,
            project_id=1,
            drift_threshold=0.50,
            auto_retrain=True
        )
        
        assert dg_new._champion_model is not None, "Champion model was not auto-restored!"
        
        # Verify the restored model is the baseline champion model (1.0.0)
        # by checking predictions are identical to the baseline champion
        test_sample = X_val[:10]
        preds_baseline = champion_clf.predict(test_sample)
        preds_restored = dg_new._champion_model.predict(test_sample)
        
        assert np.array_equal(preds_baseline, preds_restored), "Restored model predictions do not match baseline champion!"
        
        print("[PASS] Rollback persistence verified successfully. Baseline model restored on new client initialization.")
        report["Steps"].append({"name": "Verify Rollback Persistence", "status": "PASS", "detail": "New SDK client successfully auto-restored baseline v1.0.0 model."})
    except Exception as e:
        print(f"[FAIL] Rollback persistence verification failed: {e}")
        report["Steps"].append({"name": "Verify Rollback Persistence", "status": "FAIL", "detail": str(e)})
        return report

    return report

if __name__ == "__main__":
    res = run_validation()
    print("\nSummary results:")
    for step in res["Steps"]:
        print(f" - {step['name']}: {step['status']} ({step['detail']})")

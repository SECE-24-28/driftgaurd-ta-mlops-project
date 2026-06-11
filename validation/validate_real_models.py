import os
import sys
import time
import httpx
import numpy as np
import subprocess
from sklearn.datasets import load_breast_cancer
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from driftguard.tracker import DriftGuard

def get_drift_scores_for_scenario(X_data, wrapped, dg):
    # Reset drift detector to start fresh for each scenario
    dg.drift_detector = None
    scores = []
    
    for row in X_data:
        # Predict sample-by-sample to simulate online stream
        wrapped.predict(row.reshape(1, -1))
        if dg.drift_detector is not None:
            scores.append(dg.drift_detector.global_drift_score)
        else:
            scores.append(0.0)
            
    avg_score = float(np.mean(scores))
    max_score = float(np.max(scores))
    return avg_score, max_score

def main():
    print("=========================================================")
    print("VALIDATING DRIFTGUARD AGAINST REAL SCIKIT-LEARN MODELS")
    print("=========================================================")
    
    port = "8096"
    api_url = f"http://127.0.0.1:{port}"
    ts = int(time.time())
    
    # 1. Start isolated Uvicorn server
    env = os.environ.copy()
    print(f"[Server] Starting isolated Uvicorn server on port {port}...")
    server_log = open("uvicorn_real_models.log", "w", encoding="utf-8", buffering=1)
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", port],
        env=env,
        stdout=server_log,
        stderr=server_log
    )
    
    # Wait for server startup
    time.sleep(4.0)
    
    try:
        # 2. Register User & Project
        print("[Step 1] Registering User & Project on server...")
        resp_u = httpx.post(f"{api_url}/users/register", json={"email": f"real_tester_{ts}@driftguard.com", "name": "Real Model Tester"})
        if resp_u.status_code != 200:
            print(f"[FAIL] User registration failed: {resp_u.text}")
            sys.exit(1)
            
        api_key = resp_u.json()["api_key"]
        headers = {"X-API-Key": api_key}
        
        resp_p = httpx.post(f"{api_url}/projects", json={"name": "Real Models Validation"}, headers=headers)
        proj_id = resp_p.json()["id"]
        
        # 3. Load Dataset
        print("[Step 2] Loading Breast Cancer Dataset...")
        data = load_breast_cancer()
        X, y = data.data, data.target
        features = data.feature_names.tolist()
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        models_to_test = {
            "LogisticRegression": LogisticRegression(max_iter=5000, random_state=42),
            "RandomForestClassifier": RandomForestClassifier(random_state=42)
        }
        driftguards = {}
        
        results = {}
        overall_pass = True
        
        for name, model in models_to_test.items():
            print(f"\n---------------------------------------------------------")
            print(f"Testing Model: {name}")
            print(f"---------------------------------------------------------")
            
            # Train model normally
            print(f"[{name}] Training model...")
            model.fit(X_train, y_train)
            
            # Pre-register model on the server
            model_id = f"{name.lower()}-cancer-{ts}"
            print(f"[{name}] Pre-registering model '{model_id}'...")
            resp_m = httpx.post(f"{api_url}/register", json={
                "model_id": model_id,
                "project_id": proj_id,
                "drift_threshold": 0.50,
                "features": features
            }, headers=headers)
            if resp_m.status_code != 200:
                print(f"[FAIL] Model registration failed: {resp_m.text}")
                overall_pass = False
                continue
                
            # Create DriftGuard instance
            print(f"[{name}] Initializing DriftGuard SDK client...")
            dg = DriftGuard(
                model_id=model_id,
                api_url=api_url,
                api_key=api_key,
                project_id=proj_id,
                drift_threshold=0.50,
                auto_retrain=False
            )
            driftguards[name] = dg
            
            dg.set_champion(model)
            dg.set_validation_data(X_test, y_test)
            wrapped = dg.wrap(model)
            
            # Verify prediction equality
            print(f"[{name}] Verifying prediction equality...")
            pred_normal = model.predict(X_test)
            pred_wrapped = wrapped.predict(X_test)
            pred_equal = np.array_equal(pred_normal, pred_wrapped)
            print(f" - Prediction Equality: {pred_equal}")
            
            # Verify probability equality
            print(f"[{name}] Verifying predict_proba equality...")
            proba_normal = model.predict_proba(X_test)
            proba_wrapped = wrapped.predict_proba(X_test)
            proba_equal = np.allclose(proba_normal, proba_wrapped)
            print(f" - Predict Proba Equality: {proba_equal}")
            
            # Run drift scenarios
            print(f"[{name}] Running Normal scenario...")
            avg_normal, max_normal = get_drift_scores_for_scenario(X_test, wrapped, dg)
            print(f" - Normal: Avg Drift={avg_normal:.4f}, Max Drift={max_normal:.4f}")
            
            print(f"[{name}] Running Moderate scenario (X_test * 1.3)...")
            avg_mod, max_mod = get_drift_scores_for_scenario(X_test * 1.3, wrapped, dg)
            print(f" - Moderate: Avg Drift={avg_mod:.4f}, Max Drift={max_mod:.4f}")
            
            print(f"[{name}] Running Severe scenario (X_test * 20.0)...")
            avg_sev, max_sev = get_drift_scores_for_scenario(X_test * 20.0, wrapped, dg)
            print(f" - Severe: Avg Drift={avg_sev:.4f}, Max Drift={max_sev:.4f}")
            
            # Assert Normal < Moderate < Severe
            trend_asserted = (avg_normal < avg_mod < avg_sev) and (max_normal < max_mod < max_sev)
            print(f" - Drift Score Trend (Normal < Moderate < Severe) Assertion: {trend_asserted}")
            
            # Wait for telemetry queue to drain
            print(f"[{name}] Waiting for telemetry queue to drain...")
            t0 = time.time()
            while not dg._telemetry_queue.empty():
                time.sleep(0.2)
                if time.time() - t0 > 30.0:
                    print(" - [WARNING] Telemetry queue drain timed out after 30s.")
                    break
            time.sleep(2.0)  # Wait for DB write transaction commits
            
            # Query GET /drift/{model_id} to verify records exist
            print(f"[{name}] Querying drift history endpoint /drift/{model_id}...")
            resp_d = httpx.get(f"{api_url}/drift/{model_id}", headers=headers)
            telemetry_count = 0
            if resp_d.status_code == 200:
                drift_logs = resp_d.json()
                telemetry_count = len(drift_logs)
                print(f" - Successfully retrieved {telemetry_count} telemetry records from DB.")
            else:
                print(f" - [FAIL] Query /drift/{model_id} failed: {resp_d.text}")
                
            model_passed = pred_equal and proba_equal and trend_asserted and (telemetry_count > 0)
            print(f"[{name}] Status: {'PASS' if model_passed else 'FAIL'}")
            
            results[name] = {
                "passed": model_passed,
                "pred_equal": pred_equal,
                "proba_equal": proba_equal,
                "trend_asserted": trend_asserted,
                "telemetry_count": telemetry_count,
                "normal_scores": (avg_normal, max_normal),
                "moderate_scores": (avg_mod, max_mod),
                "severe_scores": (avg_sev, max_sev)
            }
            
            if not model_passed:
                overall_pass = False
                
        # 4. Generate Markdown Validation Report
        print("\n[Step 4] Generating validation report...")
        report_content = f"""# DriftGuard Real Model Validation Report

This report presents validation results for the DriftGuard platform integrations against real scikit-learn classification models.

## 1. Summary Status
**Overall Validation Result: {"PASS" if overall_pass else "FAIL"}**

## 2. Model Evaluation Details
"""
        for name, res in results.items():
            report_content += f"""
### {name}
* **Status**: {"PASS" if res["passed"] else "FAIL"}
* **Prediction Equality (predict)**: {"PASS" if res["pred_equal"] else "FAIL"}
* **Probability Equality (predict_proba)**: {"PASS" if res["proba_equal"] else "FAIL"}
* **Drift Score Trend Assertion**: {"PASS" if res["trend_asserted"] else "FAIL"}
* **Telemetry Records Query Count**: {res["telemetry_count"]} records persisted in DB
* **Scenario Performance Metrics**:
  | Scenario | Average Drift Score | Max Drift Score |
  | :--- | :---: | :---: |
  | **Normal (X_test)** | {res["normal_scores"][0]:.4f} | {res["normal_scores"][1]:.4f} |
  | **Moderate (X_test * 1.3)** | {res["moderate_scores"][0]:.4f} | {res["moderate_scores"][1]:.4f} |
  | **Severe (X_test * 20.0)** | {res["severe_scores"][0]:.4f} | {res["severe_scores"][1]:.4f} |
"""
            
        # Write to workspace
        workspace_report_path = "validation_report_real_models.md"
        with open(workspace_report_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        print(f"Validation report saved to: {workspace_report_path}")
        
        # Write to brain artifacts
        brain_report_dir = r"C:\Users\Yugendra\.gemini\antigravity-ide\brain\813ab6b8-1360-46cc-bd42-9f9a475708c8"
        if os.path.exists(brain_report_dir):
            brain_report_path = os.path.join(brain_report_dir, "validation_report_real_models.md")
            with open(brain_report_path, "w", encoding="utf-8") as f:
                f.write(report_content)
            print(f"Validation report saved to brain artifacts: {brain_report_path}")

        print("\n=========================================================")
        if overall_pass:
            print("REAL MODELS VALIDATION RESULT: PASS")
            print("=========================================================")
            sys.exit(0)
        else:
            print("REAL MODELS VALIDATION RESULT: FAIL")
            print("=========================================================")
            sys.exit(1)
            
    finally:
        print("\n[Telemetry] Shutting down DriftGuard SDK trackers...")
        for name, dg in driftguards.items():
            try:
                dg.shutdown()
            except Exception as e:
                print(f"Error shutting down DriftGuard for {name}: {e}")
        print("[Server] Shutting down isolated Uvicorn server...")
        server_process.terminate()
        server_process.wait()
        try:
            server_log.close()
        except:
            pass

if __name__ == "__main__":
    main()

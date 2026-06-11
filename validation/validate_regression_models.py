import os
import sys
import time
import httpx
import numpy as np
import subprocess
from sklearn.datasets import make_regression
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Ensure project root is in python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

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

def compute_metrics(y_true, y_pred):
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2 = float(r2_score(y_true, y_pred))
    return mae, rmse, r2

def query_db_count(model_id):
    from main import SessionLocal
    from sqlalchemy import text
    db = SessionLocal()
    try:
        count = db.execute(
            text("SELECT COUNT(*) FROM dg_predictions WHERE model_id = :model_id"),
            {"model_id": model_id}
        ).scalar()
        return int(count)
    except Exception as e:
        print(f"Error querying database count directly: {e}")
        return 0
    finally:
        db.close()

def main():
    print("=========================================================")
    print("VALIDATING DRIFTGUARD AGAINST REGRESSION MODELS")
    print("=========================================================")
    
    port = "8097"
    api_url = f"http://127.0.0.1:{port}"
    ts = int(time.time())
    
    # Start isolated Uvicorn server
    env = os.environ.copy()
    print(f"[Server] Starting isolated Uvicorn server on port {port}...")
    server_log_path = os.path.join(project_root, "uvicorn_regression_models.log")
    server_log = open(server_log_path, "w", encoding="utf-8", buffering=1)
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", port],
        env=env,
        cwd=project_root,
        stdout=server_log,
        stderr=server_log
    )
    
    # Wait for server startup
    time.sleep(4.0)
    
    try:
        # Register User & Project
        print("\n[Server] Registering User & Project on server...")
        resp_u = httpx.post(f"{api_url}/users/register", json={"email": f"reg_tester_{ts}@driftguard.com", "name": "Regression Tester"})
        if resp_u.status_code != 200:
            print(f"[FAIL] User registration failed: {resp_u.text}")
            sys.exit(1)
            
        api_key = resp_u.json()["api_key"]
        headers = {"X-API-Key": api_key}
        
        resp_p = httpx.post(f"{api_url}/projects", json={"name": "Regression Validation"}, headers=headers)
        proj_id = resp_p.json()["id"]
        
        # =================================================
        # STEP 1: Train Models
        # =================================================
        print("\n=================================================")
        print("STEP 1: Train Models")
        print("=================================================")
        
        print("- Splitting dataset into train/test.")
        X, y = make_regression(
            n_samples=5000,
            n_features=10,
            noise=15,
            random_state=42
        )
        features = [f"feat_{i}" for i in range(10)]
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        models_to_test = {
            "LinearRegression": LinearRegression(),
            "RandomForestRegressor": RandomForestRegressor(random_state=42)
        }
        
        baseline_metrics = {}
        for name, model in models_to_test.items():
            print(f"- Training {name} normally...")
            model.fit(X_train, y_train)
            preds = model.predict(X_test)
            mae, rmse, r2 = compute_metrics(y_test, preds)
            baseline_metrics[name] = {
                "mae": mae,
                "rmse": rmse,
                "r2": r2,
                "preds": preds
            }
            print(f"  Baseline Metrics for {name}:")
            print(f"    MAE:  {mae:.6f}")
            print(f"    RMSE: {rmse:.6f}")
            print(f"    R²:   {r2:.6f}")
            
        # =================================================
        # STEP 2: DriftGuard Wrapping Validation
        # =================================================
        print("\n=================================================")
        print("STEP 2: DriftGuard Wrapping Validation")
        print("=================================================")
        
        wrapped_models = {}
        driftguards = {}
        wrapping_status = {}
        
        for name, model in models_to_test.items():
            model_id = f"{name.lower()}-reg-{ts}"
            print(f"- For {name}:")
            print(f"  Creating model_id: {model_id}")
            
            # Register model on API
            resp_m = httpx.post(f"{api_url}/register", json={
                "model_id": model_id,
                "project_id": proj_id,
                "drift_threshold": 0.50,
                "features": features
            }, headers=headers)
            if resp_m.status_code != 200:
                print(f"  [FAIL] Model registration failed: {resp_m.text}")
                wrapping_status[name] = "FAIL"
                continue
                
            # Initialize DriftGuard
            dg = DriftGuard(
                model_id=model_id,
                api_url=api_url,
                api_key=api_key,
                project_id=proj_id,
                drift_threshold=0.50,
                auto_retrain=False
            )
            dg.set_champion(model)
            dg.set_validation_data(X_test, y_test)
            
            # Wrap model
            wrapped = dg.wrap(model)
            wrapped_models[name] = wrapped
            driftguards[name] = dg
            
            # Verify predictions
            original_preds = baseline_metrics[name]["preds"]
            wrapped_preds = wrapped.predict(X_test)
            
            is_equal = np.allclose(original_preds, wrapped_preds, atol=1e-8)
            status = "PASS" if is_equal else "FAIL"
            wrapping_status[name] = status
            print(f"  Output: {status}")
            
        # =================================================
        # STEP 3: Telemetry Validation
        # =================================================
        print("\n=================================================")
        print("STEP 3: Telemetry Validation")
        print("=================================================")
        
        telemetry_status = {}
        telemetry_counts = {}
        
        for name, wrapped in wrapped_models.items():
            dg = driftguards[name]
            model_id = dg.model_id
            print(f"- For {name}:")
            print("  Generating predictions sample-by-sample using wrapped model to trigger telemetry...")
            
            # We iterate sample-by-sample over X_test (1000 samples)
            for row in X_test:
                wrapped.predict(row.reshape(1, -1))
            
            print("  Waiting for telemetry queue to drain...")
            t0 = time.time()
            while not dg._telemetry_queue.empty():
                time.sleep(0.1)
                if time.time() - t0 > 30.0:
                    print("  [WARNING] Telemetry queue drain timed out.")
                    break
            time.sleep(3.0)  # Wait for database transaction commits
            
            # Print instrumentation stats
            print("  [SDK Instrumentation Stats]")
            print(f"    Telemetry events queued: {dg.telemetry_queued}")
            print(f"    Telemetry events sent:   {dg.telemetry_sent}")
            print(f"    Telemetry events failed: {dg.telemetry_failed}")
            
            # Verify database counts directly
            direct_db_count = query_db_count(model_id)
            print(f"    Telemetry records stored (Direct DB Query): {direct_db_count}")
            
            # Query GET /drift/{model_id}
            print(f"  Querying endpoint: GET {api_url}/drift/{model_id}")
            resp_d = httpx.get(f"{api_url}/drift/{model_id}", headers=headers)
            
            api_count = 0
            is_ok = False
            if resp_d.status_code == 200:
                logs = resp_d.json()
                api_count = len(logs)
                # Since the API endpoint has a limit of 100 logs, we check if direct_db_count is >= 1000
                is_ok = (direct_db_count >= 1000)
                print(f"    Endpoint returns 200. Persisted telemetry records count (API, max 100): {api_count}")
            else:
                print(f"    [FAIL] Query /drift/{model_id} failed with status {resp_d.status_code}: {resp_d.text}")
                
            status = "PASS" if is_ok else "FAIL"
            telemetry_status[name] = status
            telemetry_counts[name] = direct_db_count
            print(f"  Output: {status}")
            
        # =================================================
        # STEP 4: Drift Detection Validation
        # =================================================
        print("\n=================================================")
        print("STEP 4: Drift Detection Validation")
        print("=================================================")
        
        drift_status = {}
        scenario_scores = {}
        
        # We use a slice of 150 samples to keep execution fast
        X_scenario = X_test[:150]
        
        for name, wrapped in wrapped_models.items():
            dg = driftguards[name]
            print(f"- For {name}:")
            
            print("  A) Running Normal scenario...")
            avg_norm, max_norm = get_drift_scores_for_scenario(X_scenario, wrapped, dg)
            print(f"     Normal -> Average: {avg_norm:.4f}, Max: {max_norm:.4f}")
            
            print("  B) Running Moderate Drift scenario...")
            avg_mod, max_mod = get_drift_scores_for_scenario(X_scenario * 1.5, wrapped, dg)
            print(f"     Moderate -> Average: {avg_mod:.4f}, Max: {max_mod:.4f}")
            
            print("  C) Running Severe Drift scenario...")
            avg_sev, max_sev = get_drift_scores_for_scenario(X_scenario * 20.0, wrapped, dg)
            print(f"     Severe -> Average: {avg_sev:.4f}, Max: {max_sev:.4f}")
            
            # Verify Normal < Moderate < Severe
            trend_ok = (avg_norm < avg_mod < avg_sev) and (max_norm < max_mod < max_sev)
            status = "PASS" if trend_ok else "FAIL"
            drift_status[name] = status
            scenario_scores[name] = {
                "normal": (avg_norm, max_norm),
                "moderate": (avg_mod, max_mod),
                "severe": (avg_sev, max_sev)
            }
            print(f"  Output: {status} (Verified: Normal < Moderate < Severe)")
            
        # =================================================
        # STEP 5: Regression Accuracy Integrity
        # =================================================
        print("\n=================================================")
        print("STEP 5: Regression Accuracy Integrity")
        print("=================================================")
        
        integrity_status = {}
        wrapped_metrics = {}
        
        for name, wrapped in wrapped_models.items():
            print(f"- For {name}:")
            wrapped_preds = wrapped.predict(X_test)
            mae_w, rmse_w, r2_w = compute_metrics(y_test, wrapped_preds)
            wrapped_metrics[name] = {"mae": mae_w, "rmse": rmse_w, "r2": r2_w}
            
            mae_orig = baseline_metrics[name]["mae"]
            rmse_orig = baseline_metrics[name]["rmse"]
            r2_orig = baseline_metrics[name]["r2"]
            
            mae_diff = abs(mae_orig - mae_w)
            rmse_diff = abs(rmse_orig - rmse_w)
            r2_diff = abs(r2_orig - r2_w)
            
            passed = (mae_diff < 1e-8) and (rmse_diff < 1e-8) and (r2_diff < 1e-8)
            status = "PASS" if passed else "FAIL"
            integrity_status[name] = status
            print(f"  Original Metrics: MAE={mae_orig:.6f}, RMSE={rmse_orig:.6f}, R²={r2_orig:.6f}")
            print(f"  Wrapped Metrics:  MAE={mae_w:.6f}, RMSE={rmse_w:.6f}, R²={r2_w:.6f}")
            print(f"  Difference:       MAE={mae_diff:.2e}, RMSE={rmse_diff:.2e}, R²={r2_diff:.2e}")
            print(f"  Output: {status}")
            
        # =================================================
        # STEP 6: Final Report & Extra Check
        # =================================================
        print("\n=================================================")
        print("STEP 6: Final Report & EXTRA CHECK")
        print("=================================================")
        
        overall_pass = all(
            wrapping_status[name] == "PASS" and
            telemetry_status[name] == "PASS" and
            drift_status[name] == "PASS" and
            integrity_status[name] == "PASS"
            for name in models_to_test
        )
        
        report_content = f"""# DriftGuard Regression Models Validation Report

This report presents validation results for the DriftGuard platform integrations against real-world regression models.

## 1. Summary Status
**Overall Validation Result: {"PASS" if overall_pass else "FAIL"}**

## 2. Model Evaluation Details
"""
        for name in models_to_test:
            res_wrap = wrapping_status[name]
            res_tel = telemetry_status[name]
            res_drift = drift_status[name]
            res_integ = integrity_status[name]
            
            m_orig = baseline_metrics[name]
            m_wrap = wrapped_metrics[name]
            
            s_scores = scenario_scores[name]
            
            report_content += f"""
### {name}
* **Status**: {"PASS" if (res_wrap == "PASS" and res_tel == "PASS" and res_drift == "PASS" and res_integ == "PASS") else "FAIL"}
* **Prediction Equality**: {res_wrap}
* **Telemetry Verification**: {res_tel} ({telemetry_counts[name]} records persisted)
* **Drift Detection**: {res_drift}
* **Metrics Integrity (Original vs Wrapped)**:
  - **MAE**: Original={m_orig['mae']:.6f}, Wrapped={m_wrap['mae']:.6f}
  - **RMSE**: Original={m_orig['rmse']:.6f}, Wrapped={m_wrap['rmse']:.6f}
  - **R²**: Original={m_orig['r2']:.6f}, Wrapped={m_wrap['r2']:.6f}
* **Scenario Performance Metrics (ADWIN global drift score)**:
  | Scenario | Average Drift Score | Max Drift Score |
  | :--- | :---: | :---: |
  | **Normal (X_test)** | {s_scores['normal'][0]:.4f} | {s_scores['normal'][1]:.4f} |
  | **Moderate (X_test * 1.5)** | {s_scores['moderate'][0]:.4f} | {s_scores['moderate'][1]:.4f} |
  | **Severe (X_test * 20.0)** | {s_scores['severe'][0]:.4f} | {s_scores['severe'][1]:.4f} |
"""

        # Save report to workspace
        workspace_report_path = os.path.join(project_root, "validation_report_regression_models.md")
        with open(workspace_report_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        print(f"Validation report saved to: {workspace_report_path}")
        
        # Save report to brain artifacts
        brain_report_dir = r"C:\Users\Yugendra\.gemini\antigravity-ide\brain\813ab6b8-1360-46cc-bd42-9f9a475708c8"
        if os.path.exists(brain_report_dir):
            brain_report_path = os.path.join(brain_report_dir, "validation_report_regression_models.md")
            with open(brain_report_path, "w", encoding="utf-8") as f:
                f.write(report_content)
            print(f"Validation report saved to brain artifacts: {brain_report_path}")
            
        # Print Expected Result Block
        print("\nExpected Result:")
        for name in models_to_test:
            print(f"\n{name}:")
            print(f"    Prediction Equality {wrapping_status[name]}")
            print(f"    Telemetry {telemetry_status[name]}")
            print(f"    Drift Detection {drift_status[name]}")
            
        print("\nOverall:")
        if overall_pass:
            print("    REGRESSION VALIDATION PASS")
        else:
            print("    REGRESSION VALIDATION FAIL")
            
        # EXTRA CHECK output
        print("\n=================================================")
        print("EXTRA CHECK: Scenario Drift Scores")
        print("=================================================")
        for name in models_to_test:
            s_scores = scenario_scores[name]
            print(f"\n{name}:")
            print(f"  Normal:   Avg={s_scores['normal'][0]:.4f}, Max={s_scores['normal'][1]:.4f}")
            print(f"  Moderate: Avg={s_scores['moderate'][0]:.4f}, Max={s_scores['moderate'][1]:.4f}")
            print(f"  Severe:   Avg={s_scores['severe'][0]:.4f}, Max={s_scores['severe'][1]:.4f}")
            
        sys.exit(0 if overall_pass else 1)
        
    finally:
        print("\n[Telemetry] Shutting down DriftGuard SDK trackers...")
        for name, dg in driftguards.items():
            try:
                dg.shutdown()
            except Exception as e:
                print(f"Error shutting down DriftGuard for {name}: {e}")
        print("\n[Server] Shutting down isolated Uvicorn server...")
        server_process.terminate()
        server_process.wait()
        try:
            server_log.close()
        except:
            pass

if __name__ == "__main__":
    main()

import os
import sys
import time
import httpx
import subprocess
import sqlite3
import numpy as np
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

# Ensure project root is in python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from driftguard.tracker import DriftGuard

def main():
    print("=========================================================")
    print("PHASE 1: Environment Setup")
    print("=========================================================")
    
    port = "8099"
    api_url = f"http://127.0.0.1:{port}"
    ts = int(time.time())
    
    model_id = f"e2e-model-{ts}"
    email = f"e2e-user-{ts}@driftguard.com"
    
    # 1. Start isolated Uvicorn server on port 8099
    env = os.environ.copy()
    print(f"[Server] Starting isolated Uvicorn server on port {port}...")
    server_log_path = os.path.join(project_root, "uvicorn_retraining_workflow.log")
    server_log = open(server_log_path, "w", encoding="utf-8", buffering=1)
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", port],
        env=env,
        cwd=project_root,
        stdout=server_log,
        stderr=server_log
    )
    
    # Wait for server startup
    time.sleep(5.0)
    
    checklist = {
        "drift_detected": False,
        "retraining_triggered": False,
        "callback_executed": False,
        "validation_passed": False,
        "promotion_completed": False,
        "version_incremented": False,
        "audit_logged": False,
        "rollback_completed": False,
        "database_verified": False
    }
    
    dg = None
    champion_accuracy = 0.0
    challenger_accuracy = 0.0
    
    try:
        # Create user
        print(f"Registering user: {email}")
        resp = httpx.post(f"{api_url}/users/register", json={"email": email, "name": "E2E User"})
        if resp.status_code != 200:
            raise Exception(f"Failed to register user: {resp.text}")
        
        user_data = resp.json()
        api_key = user_data["api_key"]
        user_id = user_data["id"]
        headers = {"X-API-Key": api_key}
        
        # Create project
        print("Creating project: E2E Project")
        resp = httpx.post(f"{api_url}/projects", json={"name": "E2E Project"}, headers=headers)
        if resp.status_code != 200:
            raise Exception(f"Failed to create project: {resp.text}")
        
        project_data = resp.json()
        project_id = project_data["id"]
        
        print(f"Environment Setup Complete. user_id={user_id}, project_id={project_id}, model_id={model_id}")
        
        print("\n=================================================")
        print("PHASE 2: Champion Model Creation")
        print("=================================================")
        
        data = load_breast_cancer()
        X, y = data.data, data.target
        
        # Split train/test/validation
        X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.4, random_state=42)
        X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42)
        
        # Train deliberately weak champion
        print("Training deliberately weak champion model...")
        champion_clf = LogisticRegression(max_iter=100, random_state=42)
        # Train only on first 15 samples of training data to ensure it is weak
        champion_clf.fit(X_train[:15], y_train[:15])
        
        champ_preds = champion_clf.predict(X_val)
        champion_accuracy = float(accuracy_score(y_val, champ_preds))
        print(f"Champion Accuracy on Validation Data: {champion_accuracy:.4f}")
        
        # Register model in DriftGuard
        print(f"Registering model {model_id} on server...")
        resp = httpx.post(f"{api_url}/register", json={
            "model_id": model_id,
            "project_id": project_id,
            "drift_threshold": 0.50,
            "features": [f"feat_{i}" for i in range(X.shape[1])]
        }, headers=headers)
        if resp.status_code != 200:
            raise Exception(f"Failed to register model: {resp.text}")
            
        print("Champion model registered. Initial version is 1.0.0.")
        
        print("\n=================================================")
        print("PHASE 3: Validation Dataset")
        print("=================================================")
        
        # Initialize DriftGuard SDK
        dg = DriftGuard(
            model_id=model_id,
            api_url=api_url,
            api_key=api_key,
            project_id=project_id,
            drift_threshold=0.50,
            auto_retrain=True
        )
        dg.set_champion(champion_clf)
        dg.set_validation_data(X_val, y_val)
        
        print(f"Validation sample count: {len(X_val)}")
        
        print("\n=================================================")
        print("PHASE 4: Retraining Callback")
        print("=================================================")
        
        callback_fired = False
        
        @dg.retrainer
        def retrain_callback():
            nonlocal callback_fired, challenger_accuracy
            callback_fired = True
            print("[Callback Triggered]")
            print("[Training Challenger]")
            # Train a stronger model
            challenger_clf = RandomForestClassifier(n_estimators=200, random_state=42)
            challenger_clf.fit(X_train, y_train)
            
            chall_preds = challenger_clf.predict(X_val)
            challenger_accuracy = float(accuracy_score(y_val, chall_preds))
            print(f"[Challenger Ready]. Accuracy: {challenger_accuracy:.4f}")
            return challenger_clf
            
        print("Retraining callback registered.")
        
        print("\n=================================================")
        print("PHASE 5: Drift Generation")
        print("=================================================")
        
        wrapped = dg.wrap(champion_clf)
        
        # Generate severe drift
        X_drifted = X_test * 20
        
        print("Feeding drifted samples through wrapped model...")
        drift_score_progression = []
        
        for i, row in enumerate(X_drifted):
            _ = wrapped.predict(row.reshape(1, -1))
            drift_score = dg.drift_detector.global_drift_score if dg.drift_detector else 0.0
            drift_score_progression.append(drift_score)
            
            if dg.retraining_triggered:
                checklist["retraining_triggered"] = True
            
            if i % 10 == 0 or drift_score > dg.drift_threshold:
                print(f"Sample {i:03d} | Global Drift Score: {drift_score:.4f} (Threshold: 0.50)")
                
            if drift_score > dg.drift_threshold:
                checklist["drift_detected"] = True
                print(f"Drift threshold exceeded on sample {i}!")
                break
            time.sleep(0.02)
            
        # Wait a small moment to ensure async process is initialized
        time.sleep(1.0)
        
        if dg.retraining_triggered or callback_fired or checklist["retraining_triggered"]:
            checklist["retraining_triggered"] = True
            print("[PASS] Retraining trigger fired.")
        else:
            print("[FAIL] Retraining trigger did not fire.")
            
        print("\n=================================================")
        print("PHASE 6: Retraining Verification")
        print("=================================================")
        
        # Wait for retraining callback thread to complete execution (max 15 seconds)
        print("Waiting for retraining callback execution...")
        retrain_event_ok = False
        retrain_status_completed = False
        
        for attempt in range(15):
            # Check models endpoint status
            m_resp = httpx.get(f"{api_url}/models/{model_id}", headers=headers)
            r_resp = httpx.get(f"{api_url}/retraining/history/{model_id}", headers=headers)
            
            model_info = m_resp.json() if m_resp.status_code == 200 else {}
            history_info = r_resp.json() if r_resp.status_code == 200 else []
            
            print(f"Attempt {attempt + 1}/15: Model version={model_info.get('version')}, Model status={model_info.get('status')}")
            
            if history_info and len(history_info) > 0:
                retrain_event_ok = True
                # The latest event
                latest_event = history_info[0]
                if latest_event.get("status") == "completed":
                    retrain_status_completed = True
                    print(f"Retraining status: {latest_event.get('status')}")
                    break
            time.sleep(1.0)
            
        if callback_fired:
            checklist["callback_executed"] = True
            print("Callback executed: PASS")
        else:
            print("Callback executed: FAIL")
            
        if retrain_event_ok and retrain_status_completed:
            checklist["promotion_completed"] = True
            print("Retraining Event Status Completed: PASS")
        else:
            print("Retraining Event Status Completed: FAIL")
            
        print("\n=================================================")
        print("PHASE 7: Champion vs Challenger Validation")
        print("=================================================")
        
        print(f"Old accuracy (Champion): {champion_accuracy:.4f}")
        print(f"New accuracy (Challenger): {challenger_accuracy:.4f}")
        improvement = challenger_accuracy - champion_accuracy
        print(f"Improvement: {improvement:.4f}")
        
        if challenger_accuracy > champion_accuracy:
            checklist["validation_passed"] = True
            print("Validation decision (Challenger > Champion): PASS")
        else:
            print("Validation decision (Challenger > Champion): FAIL")
            
        print("\n=================================================")
        print("PHASE 8: Promotion Verification")
        print("=================================================")
        
        # Verify active version is 1.0.1
        resp = httpx.get(f"{api_url}/models/{model_id}", headers=headers)
        if resp.status_code == 200 and resp.json().get("version") == "1.0.1":
            checklist["version_incremented"] = True
            print("Promotion: Active version updated on server is 1.0.1: PASS")
        else:
            print("Promotion: Active version updated on server is 1.0.1: FAIL")
            
        print("\n=================================================")
        print("PHASE 9: Audit Verification")
        print("=================================================")
        
        resp = httpx.get(f"{api_url}/audit/{model_id}", headers=headers)
        audit_events = resp.json() if resp.status_code == 200 else []
        event_types = [e.get("event_type") for e in audit_events]
        print(f"Audit entries types: {event_types}")
        
        has_drift_audit = "drift_detected" in event_types
        has_promo_audit = "model_promoted" in event_types
        
        if has_drift_audit and has_promo_audit:
            checklist["audit_logged"] = True
            print("Audit events (drift_detected & model_promoted): PASS")
        else:
            print("Audit events: FAIL")
            
        print("\n=================================================")
        print("PHASE 10: Rollback Verification")
        print("=================================================")
        
        print("Executing rollback to version 1.0.0...")
        resp = httpx.post(f"{api_url}/models/{model_id}/rollback", json={"target_version": "1.0.0"}, headers=headers)
        if resp.status_code == 200:
            rollback_data = resp.json()
            if rollback_data.get("current_version") == "1.0.0":
                print("Rollback successful. Version returned to 1.0.0.")
                
                # Check server model details
                m_details = httpx.get(f"{api_url}/models/{model_id}", headers=headers).json()
                # Check audit log contains rollback
                a_logs = httpx.get(f"{api_url}/audit/{model_id}", headers=headers).json()
                has_rollback_audit = any(e.get("event_type") == "rollback" for e in a_logs)
                
                if m_details.get("version") == "1.0.0" and has_rollback_audit:
                    checklist["rollback_completed"] = True
                    print("Rollback Verification: PASS")
                else:
                    print(f"Rollback Verification: FAIL (details version: {m_details.get('version')}, has rollback audit: {has_rollback_audit})")
            else:
                print(f"Rollback Verification: FAIL (returned current_version: {rollback_data.get('current_version')})")
        else:
            print(f"Rollback Verification: FAIL (status_code: {resp.status_code}, body: {resp.text})")
            
        print("\n=================================================")
        print("PHASE 11: Direct Database Verification")
        print("=================================================")
        
        # Shut down SDK client first so all queues are flushed and telemetry is committed
        print("Shutting down DriftGuard SDK tracking...")
        dg.shutdown(timeout=10.0)
        
        # Query local SQLite database
        db_path = os.path.join(project_root, "driftguard_metadata.db")
        print(f"Connecting directly to database: {db_path}")
        
        db_pass = True
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            
            # 1. Model exists
            cursor.execute("SELECT model_id, version, status, project_id FROM dg_models WHERE model_id = ?", (model_id,))
            model_row = cursor.fetchone()
            if model_row:
                print(f"   - Model row exists: model_id={model_row[0]}, version={model_row[1]}, status={model_row[2]}")
            else:
                print("   - [FAIL] Model row does not exist.")
                db_pass = False
                
            # 2. Version history exists
            cursor.execute("SELECT version, status, accuracy FROM dg_model_versions WHERE model_id = ?", (model_id,))
            versions = cursor.fetchall()
            print("   - Model versions history in DB:")
            for v in versions:
                print(f"     * version={v[0]}, status={v[1]}, accuracy={v[2]}")
            if len(versions) >= 2:
                print("   - Version history contains expected records: PASS")
            else:
                print("   - [FAIL] Version history has fewer records than expected.")
                db_pass = False
                
            # 3. Retraining history exists
            cursor.execute("SELECT id, status, old_version, new_version FROM dg_retraining_events WHERE model_id = ?", (model_id,))
            retrain_events = cursor.fetchall()
            print("   - Retraining history in DB:")
            for r in retrain_events:
                print(f"     * id={r[0]}, status={r[1]}, old_version={r[2]}, new_version={r[3]}")
            if len(retrain_events) >= 1:
                print("   - Retraining history contains expected record: PASS")
            else:
                print("   - [FAIL] Retraining history is empty.")
                db_pass = False
                
            # 4. Audit entries exist
            cursor.execute("SELECT event_type, model_version, triggered_by FROM dg_audit_logs WHERE model_id = ?", (model_id,))
            audits = cursor.fetchall()
            print("   - Audit log entries in DB:")
            audit_types = []
            for a in audits:
                print(f"     * event_type={a[0]}, model_version={a[1]}, triggered_by={a[2]}")
                audit_types.append(a[0])
            
            # Need drift_detected, model_promoted, and rollback
            if "drift_detected" in audit_types and "model_promoted" in audit_types and "rollback" in audit_types:
                print("   - Audit logs contain expected events: PASS")
            else:
                print("   - [FAIL] Audit logs missing required events.")
                db_pass = False
                
            # 5. Current version after rollback is correct
            if model_row and model_row[1] == "1.0.0":
                print("   - Current version after rollback is 1.0.0: PASS")
            else:
                print(f"   - [FAIL] Current version after rollback is {model_row[1] if model_row else 'None'} (Expected: 1.0.0)")
                db_pass = False
                
        finally:
            conn.close()
            
        if db_pass:
            checklist["database_verified"] = True
            print("Direct Database Verification: PASS")
        else:
            print("Direct Database Verification: FAIL")
            
    except Exception as exc:
        print(f"\n[ERROR] Validation script crashed with exception: {exc}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Gracefully shut down the SDK if not already done
        if dg and not dg._is_shutdown:
            try:
                dg.shutdown(timeout=5.0)
            except:
                pass
                
        # Gracefully shut down isolated server
        print("\n[Server] Shutting down isolated Uvicorn server...")
        server_process.terminate()
        server_process.wait()
        try:
            server_log.close()
        except:
            pass
            
    # Check overall status
    passed_count = sum(1 for v in checklist.values() if v)
    overall_pass = (passed_count == 9)
    
    # 13. Generate report
    report_content = f"""---

## End-to-End Retraining Workflow Validation

Champion Accuracy: {champion_accuracy:.4f}

Challenger Accuracy: {challenger_accuracy:.4f}

Drift Trigger:
{"PASS" if checklist["drift_detected"] else "FAIL"}

Retraining:
{"PASS" if checklist["retraining_triggered"] else "FAIL"}

Validation:
{"PASS" if checklist["validation_passed"] else "FAIL"}

Promotion:
{"PASS" if checklist["promotion_completed"] else "FAIL"}

Audit Logging:
{"PASS" if checklist["audit_logged"] else "FAIL"}

Rollback:
{"PASS" if checklist["rollback_completed"] else "FAIL"}

Database Verification:
{"PASS" if checklist["database_verified"] else "FAIL"}

Overall:
{"PASS" if overall_pass else "FAIL"}

=================================================
SUCCESS CRITERIA
================

Drift Detected          {"PASS" if checklist["drift_detected"] else "FAIL"}
Retraining Triggered    {"PASS" if checklist["retraining_triggered"] else "FAIL"}
Callback Executed       {"PASS" if checklist["callback_executed"] else "FAIL"}
Validation Passed       {"PASS" if checklist["validation_passed"] else "FAIL"}
Promotion Completed     {"PASS" if checklist["promotion_completed"] else "FAIL"}
Version Incremented     {"PASS" if checklist["version_incremented"] else "FAIL"}
Audit Logged            {"PASS" if checklist["audit_logged"] else "FAIL"}
Rollback Completed      {"PASS" if checklist["rollback_completed"] else "FAIL"}
Database Verified       {"PASS" if checklist["database_verified"] else "FAIL"}
"""

    # Save to project root
    workspace_report_path = os.path.join(project_root, "validation_report_retraining_workflow.md")
    with open(workspace_report_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    print(f"\nSaved report to project root: {workspace_report_path}")
    
    # Save to brain artifacts directory
    brain_report_dir = r"C:\Users\Yugendra\AppData\Local\Temp" # Fallback if brain artifacts dir is not available/writable
    brain_artifact_dir = r"C:\Users\Yugendra\.gemini\antigravity-ide\brain\813ab6b8-1360-46cc-bd42-9f9a475708c8"
    if os.path.exists(brain_artifact_dir):
        brain_report_path = os.path.join(brain_artifact_dir, "validation_report_retraining_workflow.md")
        with open(brain_report_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        print(f"Saved report to brain artifacts: {brain_report_path}")
        
    print("\n=================================================")
    print("SUCCESS CRITERIA")
    print("=================================================")
    print(f"Drift Detected          {'PASS' if checklist['drift_detected'] else 'FAIL'}")
    print(f"Retraining Triggered    {'PASS' if checklist['retraining_triggered'] else 'FAIL'}")
    print(f"Callback Executed       {'PASS' if checklist['callback_executed'] else 'FAIL'}")
    print(f"Validation Passed       {'PASS' if checklist['validation_passed'] else 'FAIL'}")
    print(f"Promotion Completed     {'PASS' if checklist['promotion_completed'] else 'FAIL'}")
    print(f"Version Incremented     {'PASS' if checklist['version_incremented'] else 'FAIL'}")
    print(f"Audit Logged            {'PASS' if checklist['audit_logged'] else 'FAIL'}")
    print(f"Rollback Completed      {'PASS' if checklist['rollback_completed'] else 'FAIL'}")
    print(f"Database Verified       {'PASS' if checklist['database_verified'] else 'FAIL'}")
    print("=================================================")
    print("FINAL RESULT:")
    if overall_pass:
        print("PASS")
        sys.exit(0)
    else:
        print("FAIL")
        sys.exit(1)

if __name__ == "__main__":
    main()

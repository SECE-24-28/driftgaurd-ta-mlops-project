import os
import sys
import time
import httpx
import subprocess
from sqlalchemy import text

# Ensure project root is in python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

def main():
    print("=========================================================")
    print("VALIDATING DRIFTGUARD TENANT ISOLATION")
    print("=========================================================")
    
    port = "8098"
    api_url = f"http://127.0.0.1:{port}"
    ts = int(time.time())
    
    model_id_a = f"model-a-{ts}"
    model_id_b = f"model-b-{ts}"
    
    # 1. Start isolated Uvicorn server on port 8098
    env = os.environ.copy()
    print(f"[Server] Starting isolated Uvicorn server on port {port}...")
    server_log_path = os.path.join(project_root, "uvicorn_tenant_isolation.log")
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
    
    checklist = {
        "tenant_registration": False,
        "project_isolation": False,
        "model_metadata_isolation": False,
        "telemetry_auth": False,
        "authorized_access": False,
        "unauthorized_access": False,
        "rollback_isolation": False,
        "telemetry_isolation": False,
        "audit_isolation": False,
        "retraining_isolation": False
    }
    
    try:
        # 2. Register Tenant A & Tenant B
        print("\n[Step 1] Registering Tenant A & Tenant B...")
        email_a = f"tenant_a_{ts}@driftguard.com"
        email_b = f"tenant_b_{ts}@driftguard.com"
        
        resp_a = httpx.post(f"{api_url}/users/register", json={"email": email_a, "name": "Tenant A Owner"})
        resp_b = httpx.post(f"{api_url}/users/register", json={"email": email_b, "name": "Tenant B Owner"})
        
        if resp_a.status_code != 200 or resp_b.status_code != 200:
            print(f"[FAIL] Tenant registration failed. A: {resp_a.text}, B: {resp_b.text}")
            sys.exit(1)
            
        api_key_a = resp_a.json()["api_key"]
        api_key_b = resp_b.json()["api_key"]
        user_id_a = resp_a.json()["id"]
        user_id_b = resp_b.json()["id"]
        
        headers_a = {"X-API-Key": api_key_a}
        headers_b = {"X-API-Key": api_key_b}
        
        checklist["tenant_registration"] = True
        print(f" - Tenant A registered (ID: {user_id_a})")
        print(f" - Tenant B registered (ID: {user_id_b})")
        
        # 3. Create Separate Projects
        print("\n[Step 2] Creating Projects...")
        p_a = httpx.post(f"{api_url}/projects", json={"name": "Project A"}, headers=headers_a)
        p_b = httpx.post(f"{api_url}/projects", json={"name": "Project B"}, headers=headers_b)
        
        if p_a.status_code != 200 or p_b.status_code != 200:
            print(f"[FAIL] Project creation failed. A: {p_a.text}, B: {p_b.text}")
            sys.exit(1)
            
        proj_id_a = p_a.json()["id"]
        proj_id_b = p_b.json()["id"]
        checklist["project_isolation"] = True
        print(f" - Project A created (ID: {proj_id_a})")
        print(f" - Project B created (ID: {proj_id_b})")
        
        # 4. Register model-a and model-b with timestamps
        print(f"\n[Step 3] Registering Models ({model_id_a} and {model_id_b})...")
        m_a = httpx.post(f"{api_url}/register", json={
            "model_id": model_id_a,
            "project_id": proj_id_a,
            "drift_threshold": 0.20,
            "features": ["feat_1", "feat_2"]
        }, headers=headers_a)
        
        m_b = httpx.post(f"{api_url}/register", json={
            "model_id": model_id_b,
            "project_id": proj_id_b,
            "drift_threshold": 0.30,
            "features": ["feat_1", "feat_2"]
        }, headers=headers_b)
        
        if m_a.status_code != 200 or m_b.status_code != 200:
            print(f"[FAIL] Model registration failed. A: {m_a.text}, B: {m_b.text}")
            sys.exit(1)
            
        print(f" - {model_id_a} registered for Tenant A")
        print(f" - {model_id_b} registered for Tenant B")
        
        # Verify direct model metadata access isolation
        print("\n[Step 4] Verifying Direct Model Metadata Access...")
        det_a_auth = httpx.get(f"{api_url}/models/{model_id_a}", headers=headers_a)
        det_b_auth = httpx.get(f"{api_url}/models/{model_id_b}", headers=headers_b)
        
        det_a_unauth = httpx.get(f"{api_url}/models/{model_id_a}", headers=headers_b)
        det_b_unauth = httpx.get(f"{api_url}/models/{model_id_b}", headers=headers_a)
        
        print(f" - Tenant A reading metadata of {model_id_a}: {det_a_auth.status_code}")
        print(f" - Tenant B reading metadata of {model_id_b}: {det_b_auth.status_code}")
        print(f" - Tenant B reading metadata of {model_id_a}: {det_a_unauth.status_code} (Expected 403)")
        print(f" - Tenant A reading metadata of {model_id_b}: {det_b_unauth.status_code} (Expected 403)")
        
        if (det_a_auth.status_code == 200 and det_b_auth.status_code == 200 and
            det_a_unauth.status_code == 403 and det_b_unauth.status_code == 403):
            checklist["model_metadata_isolation"] = True
            print(" - Direct Model Metadata Access Isolation: PASS")
        else:
            print(" - Direct Model Metadata Access Isolation: FAIL")
            
        # 5. Generate Telemetry for both models
        print("\n[Step 5] Generating Telemetry...")
        tel_a = httpx.post(f"{api_url}/predict/{model_id_a}", json={
            "features": [0.5, 1.2],
            "prediction": [1.0],
            "drift_score": 0.05
        }, headers=headers_a)
        
        tel_b = httpx.post(f"{api_url}/predict/{model_id_b}", json={
            "features": [0.8, -0.4],
            "prediction": [0.0],
            "drift_score": 0.12
        }, headers=headers_b)
        
        print(f" - Tenant A sending telemetry to {model_id_a}: {tel_a.status_code}")
        print(f" - Tenant B sending telemetry to {model_id_b}: {tel_b.status_code}")
        
        # Verify Tenant A sending to model-b
        tel_b_unauth = httpx.post(f"{api_url}/predict/{model_id_b}", json={
            "features": [0.8, -0.4],
            "prediction": [0.0],
            "drift_score": 0.12
        }, headers=headers_a)
        print(f" - Tenant A sending telemetry to {model_id_b}: {tel_b_unauth.status_code} (Expected 403)")
        
        if tel_a.status_code == 200 and tel_b.status_code == 200 and tel_b_unauth.status_code == 403:
            checklist["telemetry_auth"] = True
            print(" - Telemetry Authorization: PASS")
        else:
            print(" - Telemetry Authorization: FAIL")
            
        # 6. Verify Authorized Access (Expect 200)
        print("\n[Step 6] Verifying Authorized Access (Expect 200)...")
        # Tenant A accessing model-a
        dr_a = httpx.get(f"{api_url}/drift/{model_id_a}", headers=headers_a)
        au_a = httpx.get(f"{api_url}/audit/{model_id_a}", headers=headers_a)
        re_a = httpx.get(f"{api_url}/retraining/history/{model_id_a}", headers=headers_a)
        
        # Tenant B accessing model-b
        dr_b = httpx.get(f"{api_url}/drift/{model_id_b}", headers=headers_b)
        au_b = httpx.get(f"{api_url}/audit/{model_id_b}", headers=headers_b)
        re_b = httpx.get(f"{api_url}/retraining/history/{model_id_b}", headers=headers_b)
        
        print(f" - Tenant A GET drift/{model_id_a}: {dr_a.status_code}")
        print(f" - Tenant A GET audit/{model_id_a}: {au_a.status_code}")
        print(f" - Tenant A GET retraining/{model_id_a}: {re_a.status_code}")
        print(f" - Tenant B GET drift/{model_id_b}: {dr_b.status_code}")
        print(f" - Tenant B GET audit/{model_id_b}: {au_b.status_code}")
        print(f" - Tenant B GET retraining/{model_id_b}: {re_b.status_code}")
        
        if (dr_a.status_code == 200 and au_a.status_code == 200 and re_a.status_code == 200 and
            dr_b.status_code == 200 and au_b.status_code == 200 and re_b.status_code == 200):
            checklist["authorized_access"] = True
            print(" - Authorized Access: PASS")
        else:
            print(" - Authorized Access: FAIL")
            
        # 7. Verify Unauthorized Access (Expect 403)
        print("\n[Step 7] Verifying Unauthorized Access (Expect 403)...")
        # Tenant A attempting to access model-b
        dr_b_un = httpx.get(f"{api_url}/drift/{model_id_b}", headers=headers_a)
        au_b_un = httpx.get(f"{api_url}/audit/{model_id_b}", headers=headers_a)
        re_b_un = httpx.get(f"{api_url}/retraining/history/{model_id_b}", headers=headers_a)
        
        # Tenant B attempting to access model-a
        dr_a_un = httpx.get(f"{api_url}/drift/{model_id_a}", headers=headers_b)
        au_a_un = httpx.get(f"{api_url}/audit/{model_id_a}", headers=headers_b)
        re_a_un = httpx.get(f"{api_url}/retraining/history/{model_id_a}", headers=headers_b)
        
        print(f" - Tenant A GET drift/{model_id_b}: {dr_b_un.status_code} (Expected 403)")
        print(f" - Tenant A GET audit/{model_id_b}: {au_b_un.status_code} (Expected 403)")
        print(f" - Tenant A GET retraining/{model_id_b}: {re_b_un.status_code} (Expected 403)")
        print(f" - Tenant B GET drift/{model_id_a}: {dr_a_un.status_code} (Expected 403)")
        print(f" - Tenant B GET audit/{model_id_a}: {au_a_un.status_code} (Expected 403)")
        print(f" - Tenant B GET retraining/{model_id_a}: {re_a_un.status_code} (Expected 403)")
        
        if (dr_b_un.status_code == 403 and au_b_un.status_code == 403 and re_b_un.status_code == 403 and
            dr_a_un.status_code == 403 and au_a_un.status_code == 403 and re_a_un.status_code == 403):
            checklist["unauthorized_access"] = True
            print(" - Unauthorized Access: PASS")
        else:
            print(" - Unauthorized Access: FAIL")
            
        # 8. Verify Rollback Isolation (Expect 403)
        print("\n[Step 8] Verifying Rollback Isolation...")
        rb_b_un = httpx.post(f"{api_url}/models/{model_id_b}/rollback", json={"target_version": "1.0.0"}, headers=headers_a)
        rb_a_un = httpx.post(f"{api_url}/models/{model_id_a}/rollback", json={"target_version": "1.0.0"}, headers=headers_b)
        
        print(f" - Tenant A POST rollback {model_id_b}: {rb_b_un.status_code} (Expected 403)")
        print(f" - Tenant B POST rollback {model_id_a}: {rb_a_un.status_code} (Expected 403)")
        
        if rb_b_un.status_code == 403 and rb_a_un.status_code == 403:
            checklist["rollback_isolation"] = True
            print(" - Rollback Isolation: PASS")
        else:
            print(" - Rollback Isolation: FAIL")
            
        # 9. Verify Telemetry Isolation
        print("\n[Step 9] Verifying Telemetry Isolation...")
        logs_a = dr_a.json()
        logs_b = dr_b.json()
        
        has_leak_a = any(log.get("model_id") == model_id_b for log in logs_a)
        has_leak_b = any(log.get("model_id") == model_id_a for log in logs_b)
        
        print(f" - Tenant A telemetry cross-leak detected: {has_leak_a}")
        print(f" - Tenant B telemetry cross-leak detected: {has_leak_b}")
        
        if not has_leak_a and not has_leak_b:
            checklist["telemetry_isolation"] = True
            print(" - Telemetry Isolation: PASS")
        else:
            print(" - Telemetry Isolation: FAIL")
            
        # 10. Verify Audit Isolation
        print("\n[Step 10] Verifying Audit Isolation...")
        audit_logs_a = au_a.json()
        audit_logs_b = au_b.json()
        
        audit_leak_a = any(log.get("model_id") == model_id_b for log in audit_logs_a)
        audit_leak_b = any(log.get("model_id") == model_id_a for log in audit_logs_b)
        
        print(f" - Tenant A audit cross-leak detected: {audit_leak_a}")
        print(f" - Tenant B audit cross-leak detected: {audit_leak_b}")
        
        if not audit_leak_a and not audit_leak_b:
            checklist["audit_isolation"] = True
            print(" - Audit Isolation: PASS")
        else:
            print(" - Audit Isolation: FAIL")
            
        # 11. Verify Retraining History Isolation
        print("\n[Step 11] Verifying Retraining History Isolation...")
        history_a = re_a.json()
        history_b = re_b.json()
        
        retrain_leak_a = any(event.get("model_id") == model_id_b for event in history_a)
        retrain_leak_b = any(event.get("model_id") == model_id_a for event in history_b)
        
        print(f" - Tenant A retraining cross-leak detected: {retrain_leak_a}")
        print(f" - Tenant B retraining cross-leak detected: {retrain_leak_b}")
        
        if not retrain_leak_a and not retrain_leak_b:
            checklist["retraining_isolation"] = True
            print(" - Retraining Isolation: PASS")
        else:
            print(" - Retraining Isolation: FAIL")
            
        # 12. Verify Database Ownership Directly (SQL Verification)
        print("\n[Step 12] Verifying Database Records Directly...")
        from main import SessionLocal
        db = SessionLocal()
        try:
            # Check models owner_id
            m_a_db = db.execute(text("SELECT owner_id, project_id FROM dg_models WHERE model_id = :model_id"), {"model_id": model_id_a}).fetchone()
            m_b_db = db.execute(text("SELECT owner_id, project_id FROM dg_models WHERE model_id = :model_id"), {"model_id": model_id_b}).fetchone()
            
            db_pass = True
            if m_a_db and m_b_db:
                print(f"   - DB model-a ({model_id_a}): owner_id={m_a_db[0]} (Expected: {user_id_a}), project_id={m_a_db[1]} (Expected: {proj_id_a})")
                print(f"   - DB model-b ({model_id_b}): owner_id={m_b_db[0]} (Expected: {user_id_b}), project_id={m_b_db[1]} (Expected: {proj_id_b})")
                
                if m_a_db[0] != user_id_a or m_b_db[0] != user_id_b or m_a_db[1] != proj_id_a or m_b_db[1] != proj_id_b:
                    db_pass = False
            else:
                db_pass = False
                print("   - [FAIL] Models not found in DB query.")
                
            # Check telemetry project_id mapping
            t_a_db = db.execute(text("SELECT project_id FROM dg_predictions WHERE model_id = :model_id"), {"model_id": model_id_a}).fetchall()
            t_b_db = db.execute(text("SELECT project_id FROM dg_predictions WHERE model_id = :model_id"), {"model_id": model_id_b}).fetchall()
            
            print(f"   - DB model-a predictions project_ids: {[r[0] for r in t_a_db]}")
            print(f"   - DB model-b predictions project_ids: {[r[0] for r in t_b_db]}")
            
            for r in t_a_db:
                if r[0] != proj_id_a:
                    db_pass = False
            for r in t_b_db:
                if r[0] != proj_id_b:
                    db_pass = False
                    
            if db_pass:
                print(" - Direct SQL DB Verification: PASS")
            else:
                print(" - Direct SQL DB Verification: FAIL")
                checklist["project_isolation"] = False  # Mark project isolation failed if DB mapping is wrong
        finally:
            db.close()
            
        # Compute Security Score
        passed_count = sum(1 for v in checklist.values() if v)
        score = passed_count  # 10 checklist items, 1 point each
        overall_pass = (score == 10)
        
        # 13. Generate report validation_report_tenant_isolation.md
        report_content = f"""# Tenant Isolation Validation Report

This report presents strict validation results verifying complete tenant isolation across the DriftGuard platform.

## Summary Status
* **Authorized Requests**: {"PASS" if checklist["authorized_access"] else "FAIL"}
* **Unauthorized Requests**: {"PASS" if checklist["unauthorized_access"] else "FAIL"}
* **Telemetry Isolation**: {"PASS" if checklist["telemetry_isolation"] else "FAIL"}
* **Audit Isolation**: {"PASS" if checklist["audit_isolation"] else "FAIL"}
* **Retraining Isolation**: {"PASS" if checklist["retraining_isolation"] else "FAIL"}
* **Rollback Isolation**: {"PASS" if checklist["rollback_isolation"] else "FAIL"}

## Security Score
**Security Score: {score} / 10**

## Overall Result
**Overall Result: {"PASS" if overall_pass else "FAIL"}**
"""
        
        # Save to project root
        workspace_report_path = os.path.join(project_root, "validation_report_tenant_isolation.md")
        with open(workspace_report_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        print(f"\nSaved report to project root: {workspace_report_path}")
        
        # Save to brain artifacts directory
        brain_report_dir = r"C:\Users\Yugendra\.gemini\antigravity-ide\brain\813ab6b8-1360-46cc-bd42-9f9a475708c8"
        if os.path.exists(brain_report_dir):
            brain_report_path = os.path.join(brain_report_dir, "validation_report_tenant_isolation.md")
            with open(brain_report_path, "w", encoding="utf-8") as f:
                f.write(report_content)
            print(f"Saved report to brain artifacts: {brain_report_path}")
            
        print("\n=================================================")
        print("TENANT ISOLATION VALIDATION RESULT")
        print("=================================================")
        if overall_pass:
            print("PASS")
            print("=================================================")
            sys.exit(0)
        else:
            print("FAIL")
            print("=================================================")
            sys.exit(1)
            
    except Exception as exc:
        print(f"\n[ERROR] Validation encountered an unexpected exception: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
        
    finally:
        print("\n[Server] Shutting down isolated Uvicorn server...")
        server_process.terminate()
        server_process.wait()
        try:
            server_log.close()
        except:
            pass

if __name__ == "__main__":
    main()

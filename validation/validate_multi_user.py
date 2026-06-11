import os
import sys
import httpx

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

def run_validation():
    print("=========================================================")
    print("PHASE F: MULTI-USER TENANT ISOLATION VALIDATION")
    print("=========================================================")
    
    report = {
        "Phase": "Phase F: Multi-User Tenant Isolation",
        "Steps": []
    }
    
    api_url = "http://127.0.0.1:8000"
    
    # Step 1: Register User A and User B
    try:
        # Generate unique emails based on timestamp to prevent collision on repeat runs
        ts = int(os.getpid() + 1000)
        email_a = f"usera_{ts}@example.com"
        email_b = f"userb_{ts}@example.com"

        resp_a = httpx.post(f"{api_url}/users/register", json={"email": email_a, "name": "User A"})
        assert resp_a.status_code == 200, f"Register A failed: {resp_a.text}"
        user_a = resp_a.json()
        api_key_a = user_a["api_key"]
        
        resp_b = httpx.post(f"{api_url}/users/register", json={"email": email_b, "name": "User B"})
        assert resp_b.status_code == 200, f"Register B failed: {resp_b.text}"
        user_b = resp_b.json()
        api_key_b = user_b["api_key"]

        print(f"[PASS] Registered User A ({email_a}) and User B ({email_b}).")
        report["Steps"].append({"name": "Register Users", "status": "PASS", "detail": "User A and User B registered successfully."})
    except Exception as e:
        print(f"[FAIL] User registration failed: {e}")
        report["Steps"].append({"name": "Register Users", "status": "FAIL", "detail": str(e)})
        return report

    # Step 2: User A creates Project A and registers Model A
    try:
        headers_a = {"X-API-Key": api_key_a}
        resp_proj_a = httpx.post(f"{api_url}/projects", json={"name": "Project A"}, headers=headers_a)
        assert resp_proj_a.status_code == 200, resp_proj_a.text
        proj_a_id = resp_proj_a.json()["id"]

        resp_model_a = httpx.post(f"{api_url}/register", json={
            "model_id": f"model-a-{ts}",
            "project_id": proj_a_id,
            "drift_threshold": 0.15,
            "features": ["f1", "f2"]
        }, headers=headers_a)
        assert resp_model_a.status_code in [200, 201], resp_model_a.text
        model_a_id = f"model-a-{ts}"

        print(f"[PASS] User A created Project A ({proj_a_id}) and registered Model A ({model_a_id}).")
        report["Steps"].append({"name": "Setup User A Assets", "status": "PASS", "detail": f"Project A ID: {proj_a_id}, Model A: {model_a_id}"})
    except Exception as e:
        print(f"[FAIL] Setup User A assets failed: {e}")
        report["Steps"].append({"name": "Setup User A Assets", "status": "FAIL", "detail": str(e)})
        return report

    # Step 3: User B creates Project B and registers Model B
    try:
        headers_b = {"X-API-Key": api_key_b}
        resp_proj_b = httpx.post(f"{api_url}/projects", json={"name": "Project B"}, headers=headers_b)
        assert resp_proj_b.status_code == 200, resp_proj_b.text
        proj_b_id = resp_proj_b.json()["id"]

        resp_model_b = httpx.post(f"{api_url}/register", json={
            "model_id": f"model-b-{ts}",
            "project_id": proj_b_id,
            "drift_threshold": 0.15,
            "features": ["f1", "f2"]
        }, headers=headers_b)
        assert resp_model_b.status_code in [200, 201], resp_model_b.text
        model_b_id = f"model-b-{ts}"

        print(f"[PASS] User B created Project B ({proj_b_id}) and registered Model B ({model_b_id}).")
        report["Steps"].append({"name": "Setup User B Assets", "status": "PASS", "detail": f"Project B ID: {proj_b_id}, Model B: {model_b_id}"})
    except Exception as e:
        print(f"[FAIL] Setup User B assets failed: {e}")
        report["Steps"].append({"name": "Setup User B Assets", "status": "FAIL", "detail": str(e)})
        return report

    # Step 4: Perform Isolation Cross-Checks (User A attempts to access/modify User B's resources)
    try:
        print("Checking User A boundary enforcement (expecting 403 on all)...")
        headers_a = {"X-API-Key": api_key_a}
        
        cross_endpoints = [
            ("GET", f"/projects/{proj_b_id}", None),
            ("POST", f"/register", {"model_id": model_b_id, "project_id": proj_a_id}),
            ("POST", f"/predict/{model_b_id}", {"features": [1.0, 2.0], "prediction": [0.0], "drift_score": 0.01}),
            ("GET", f"/drift/{model_b_id}", None),
            ("GET", f"/models/{model_b_id}", None),
            ("GET", f"/models/{model_b_id}/versions", None),
            ("POST", f"/models/{model_b_id}/rollback", {"target_version": "1.0.0"}),
            ("GET", f"/retraining/history/{model_b_id}", None),
            ("GET", f"/audit/{model_b_id}", None),
            ("POST", f"/retrain/{model_b_id}", {"drift_score": 0.25, "triggered_by": "automatic", "source": "sdk_callback"}),
            ("POST", f"/retrain/{model_b_id}/complete", {"validation_passed": True, "new_version": "1.0.1", "new_accuracy": 0.95})
        ]

        failures = []
        for method, route, payload in cross_endpoints:
            url = f"{api_url}{route}"
            if method == "GET":
                r = httpx.get(url, headers=headers_a)
            else:
                r = httpx.post(url, json=payload, headers=headers_a)
            
            if r.status_code != 403:
                failures.append(f"{method} {route} returned status: {r.status_code} instead of 403")
                print(f" - [FAIL] User A: {method} {route} allowed! Status: {r.status_code}")
            else:
                print(f" - [PASS] User A: {method} {route} blocked (403 Forbidden)")

        assert len(failures) == 0, f"Tenant boundary violations found for User A: {failures}"
        print("[PASS] All cross-tenant endpoint attempts by User A were correctly blocked with 403.")
        report["Steps"].append({"name": "User A Isolation Checks", "status": "PASS", "detail": "All cross-tenant requests returned 403."})
    except Exception as e:
        print(f"[FAIL] User A isolation check failed: {e}")
        report["Steps"].append({"name": "User A Isolation Checks", "status": "FAIL", "detail": str(e)})
        return report

    # Step 5: Perform Isolation Cross-Checks (User B attempts to access/modify User A's resources)
    try:
        print("Checking User B boundary enforcement (expecting 403 on all)...")
        headers_b = {"X-API-Key": api_key_b}
        
        cross_endpoints = [
            ("GET", f"/projects/{proj_a_id}", None),
            ("POST", f"/register", {"model_id": model_a_id, "project_id": proj_b_id}),
            ("POST", f"/predict/{model_a_id}", {"features": [1.0, 2.0], "prediction": [0.0], "drift_score": 0.01}),
            ("GET", f"/drift/{model_a_id}", None),
            ("GET", f"/models/{model_a_id}", None),
            ("GET", f"/models/{model_a_id}/versions", None),
            ("POST", f"/models/{model_a_id}/rollback", {"target_version": "1.0.0"}),
            ("GET", f"/retraining/history/{model_a_id}", None),
            ("GET", f"/audit/{model_a_id}", None),
            ("POST", f"/retrain/{model_a_id}", {"drift_score": 0.25, "triggered_by": "automatic", "source": "sdk_callback"}),
            ("POST", f"/retrain/{model_a_id}/complete", {"validation_passed": True, "new_version": "1.0.1", "new_accuracy": 0.95})
        ]

        failures = []
        for method, route, payload in cross_endpoints:
            url = f"{api_url}{route}"
            if method == "GET":
                r = httpx.get(url, headers=headers_b)
            else:
                r = httpx.post(url, json=payload, headers=headers_b)
            
            if r.status_code != 403:
                failures.append(f"{method} {route} returned status: {r.status_code} instead of 403")
                print(f" - [FAIL] User B: {method} {route} allowed! Status: {r.status_code}")
            else:
                print(f" - [PASS] User B: {method} {route} blocked (403 Forbidden)")

        assert len(failures) == 0, f"Tenant boundary violations found for User B: {failures}"
        print("[PASS] All cross-tenant endpoint attempts by User B were correctly blocked with 403.")
        report["Steps"].append({"name": "User B Isolation Checks", "status": "PASS", "detail": "All cross-tenant requests returned 403."})
    except Exception as e:
        print(f"[FAIL] User B isolation check failed: {e}")
        report["Steps"].append({"name": "User B Isolation Checks", "status": "FAIL", "detail": str(e)})
        return report

    return report

if __name__ == "__main__":
    res = run_validation()
    print("\nSummary results:")
    for step in res["Steps"]:
        print(f" - {step['name']}: {step['status']} ({step['detail']})")

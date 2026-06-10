import sys
import time

# Reconfigure stdout to use UTF-8 to handle unicode symbols like arrow characters on Windows terminals
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
import httpx
import numpy as np
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier

from driftguard import DriftGuard

# =====================================================
# CONFIGURATION
# =====================================================
API_URL = "http://localhost:8000"
MODEL_ID = f"verify-promo-{int(time.time())}"

print("=====================================================")
print(f"STARTING PROMOTION FLOW AUDIT FOR MODEL: {MODEL_ID}")
print("=====================================================")

# =====================================================
# 1. REGISTER MODEL VIA POST /register
# =====================================================
print("\n[Step 1] Registering model on backend...")
try:
    with httpx.Client(timeout=5.0) as client:
        resp = client.post(
            f"{API_URL}/register",
            json={
                "model_id": MODEL_ID,
                "drift_threshold": 0.15,
                "reference_data_path": "",
                "features": [f"feat_{i}" for i in range(30)]
            }
        )
        assert resp.status_code == 200, f"Registration failed: {resp.text}"
        print(f"-> Model registered successfully: {resp.json()}")
except Exception as e:
    print(f"Error during registration: {e}")
    sys.exit(1)

# =====================================================
# 2. PREPARE DATA AND TRAIN MODELS
# =====================================================
print("\n[Step 2] Preparing dataset...")
X, y = load_breast_cancer(return_X_y=True)
X_train, X_temp, y_train, y_temp = train_test_split(X, y, test_size=0.3, random_state=42)
X_val, X_test, y_val, y_test = train_test_split(X_temp, y_temp, test_size=0.5, random_state=42)

# Train a intentionally weak champion (Decision Tree max_depth=1)
print("-> Training weak champion model...")
champion = DecisionTreeClassifier(max_depth=1, random_state=42)
champion.fit(X_train, y_train)
champ_acc = champion.score(X_val, y_val)
print(f"-> Champion validation accuracy: {champ_acc:.4f}")

# =====================================================
# 3. SET UP DRIFTGUARD SDK
# =====================================================
print("\n[Step 3] Initializing DriftGuard SDK...")
dg = DriftGuard(model_id=MODEL_ID, api_url=API_URL, drift_threshold=0.15)
dg.set_champion(champion)
dg.set_validation_data(X_val, y_val)

# Define callback that trains a strong challenger (RandomForestClassifier)
@dg.retrainer
def retrain():
    print("\n[Callback] Retraining callback triggered!")
    challenger = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    challenger.fit(X_train, y_train)
    chall_acc = challenger.score(X_val, y_val)
    print(f"[Callback] Challenger validation accuracy: {chall_acc:.4f}")
    return challenger

# Wrap model
wrapped = dg.wrap(champion)

# =====================================================
# 4. FORCE DRIFT TO TRIGGER RETRAINING
# =====================================================
print("\n[Step 4] Sending drifted predictions to trigger threshold breach...")
drifted_traffic = X_test * 1.50
drift_triggered = False

for i in range(len(drifted_traffic)):
    wrapped.predict(drifted_traffic[i].reshape(1, -1))
    
    # Check if the tracker's ADWIN detector computed drift score above threshold
    if dg.drift_detector is not None:
        score = dg.drift_detector.global_drift_score
        print(f"-> Sample {i+1:03d} | Drift score: {score:.4f}")
        if score > dg.drift_threshold:
            print("-> Drift threshold breached!")
            drift_triggered = True
            break

assert drift_triggered, "Failed to trigger drift threshold breach."

# =====================================================
# 5. POLL FOR RETRAINING PIPELINE COMPLETION
# =====================================================
print("\n[Step 5] Polling backend for retraining completion...")
max_wait = 15.0
start_wait = time.time()
event_completed = False
retrain_event = None

while time.time() - start_wait < max_wait:
    time.sleep(0.5)
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{API_URL}/retraining/history/{MODEL_ID}")
            if resp.status_code == 200:
                events = resp.json()
                if events:
                    # Find any SDK callback event that finished (ignore seed mock event with ID 1)
                    for ev in events:
                        if ev.get("id") != 1 and ev.get("status") in ["completed", "failed"]:
                            event_completed = True
                            retrain_event = ev
                            break
            if event_completed:
                break
    except Exception as e:
        print(f"Polling error: {e}")

if not event_completed:
    print("Error: Retraining event did not complete in time.")
    sys.exit(1)

print(f"-> Retraining Event Finished: status={retrain_event.get('status')}")
print(f"-> Details: {retrain_event}")

assert retrain_event.get("status") == "completed", f"Retraining failed: {retrain_event.get('details_json')}"

# =====================================================
# 6. FETCH AUDIT DETAILS & RUN ASSERTIONS
# =====================================================
print("\n[Step 6] Running promotion verification assertions...")

with httpx.Client(timeout=5.0) as client:
    # A. Get model status
    model_resp = client.get(f"{API_URL}/models/{MODEL_ID}")
    assert model_resp.status_code == 200, f"Failed to get model: {model_resp.text}"
    model_data = model_resp.json()
    print(f"-> GET /models/{MODEL_ID} response: {model_data}")
    
    # B. Get version history
    versions_resp = client.get(f"{API_URL}/models/{MODEL_ID}/versions")
    assert versions_resp.status_code == 200, f"Failed to get versions: {versions_resp.text}"
    versions = versions_resp.json()
    print(f"-> GET /models/{MODEL_ID}/versions response: {versions}")
    
    # C. Get audit logs
    audit_resp = client.get(f"{API_URL}/audit/{MODEL_ID}")
    assert audit_resp.status_code == 200, f"Failed to get audit logs: {audit_resp.text}"
    audit_logs = audit_resp.json()
    print(f"-> GET /audit/{MODEL_ID} response: {audit_logs}")

# Assertions
print("\n[Step 7] Evaluating promotion flow assertions...")

# 1. Event status is completed
assert retrain_event.get("status") == "completed", "Retraining event status should be 'completed'"

# 2. Version bump occurred in model registry
old_version = "1.0.0"
new_version = model_data.get("version")
print(f"   Assertion: version bump ({old_version} -> {new_version})")
assert new_version != old_version, f"Version should be bumped from {old_version}"

# 3. Model accuracy is updated
new_accuracy = model_data.get("accuracy")
print(f"   Assertion: accuracy updated (champion {champ_acc:.4f} -> promoted {new_accuracy:.4f})")
assert new_accuracy > champ_acc, f"Promoted model accuracy {new_accuracy} should beat champion {champ_acc}"

# 4. Version registry has updated champion version
champ_versions = [v for v in versions if v.get("status") == "champion"]
assert len(champ_versions) == 1, "There should be exactly one champion version"
assert champ_versions[0].get("version") == new_version, "Version registry champion version should match new model version"
assert champ_versions[0].get("accuracy") == new_accuracy, "Version registry champion accuracy should match new model accuracy"

# 5. Audit entry exists for the promotion event
promoted_audit = [log for log in audit_logs if log.get("event_type") == "model_promoted"]
assert len(promoted_audit) >= 1, "An audit log entry of type 'model_promoted' should be created"
print(f"   Assertion: audit event logged ({promoted_audit[0]})")

print("\n=====================================================")
print("SUCCESS: ALL MODEL PROMOTION FLOW ASSERTIONS PASSED!")
print("=====================================================")

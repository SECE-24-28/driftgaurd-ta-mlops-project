import time
import httpx
import sqlite3
from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
from driftguard import DriftGuard

MODEL_ID = f"ACCURACY_TEST_{int(time.time())}"
API_KEY = "dg-901d293403b8a0625d12ecf6d5c1cd78"
PROJECT_ID = 21

print("--- TRAINING MODEL ---")
X, y = make_classification(n_samples=1000, n_features=5, random_state=42)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
measured_accuracy = float(accuracy_score(y_test, y_pred))

print(f"Measured Accuracy: {measured_accuracy}")

print("\n--- REGISTERING MODEL VIA DRIFTGUARD SDK ---")
dg = DriftGuard(
    model_id=MODEL_ID,
    api_url="http://localhost:8000",
    api_key=API_KEY,
    project_id=PROJECT_ID,
    drift_threshold=0.25,
    accuracy=measured_accuracy,
    version="1.0.0"
)

# Wrapping triggers explicit registration
wrapped = dg.wrap(model)

# Give API a second to persist
time.sleep(1)

print("\n--- VERIFYING STORAGE ---")
# 1. API Accuracy
try:
    resp = httpx.get(f"http://localhost:8000/models", headers={"X-API-Key": API_KEY})
    if resp.status_code == 200:
        models = resp.json()
        target = next((m for m in models if m["model_id"] == MODEL_ID), None)
        if target:
            print(f"API Accuracy: {target.get('accuracy')}")
        else:
            print("API Accuracy: Model not found in /models")
    else:
        print(f"API Failed: {resp.status_code} - {resp.text}")
except Exception as e:
    print(f"API Error: {e}")

# 2. Stored Accuracy
try:
    conn = sqlite3.connect('driftguard_metadata.db')
    cursor = conn.cursor()
    cursor.execute("SELECT accuracy FROM dg_models WHERE model_id = ?", (MODEL_ID,))
    stored_acc = cursor.fetchone()
    if stored_acc:
        print(f"Stored Accuracy (dg_models): {stored_acc[0]}")
    else:
        print("Stored Accuracy (dg_models): Not found")
        
    cursor.execute("SELECT accuracy FROM dg_model_versions WHERE model_id = ? ORDER BY id DESC LIMIT 1", (MODEL_ID,))
    ver_acc = cursor.fetchone()
    if ver_acc:
        print(f"Stored Accuracy (dg_model_versions): {ver_acc[0]}")
    else:
        print("Stored Accuracy (dg_model_versions): Not found")
except Exception as e:
    print(f"DB Error: {e}")

print("\n--- DONE ---")

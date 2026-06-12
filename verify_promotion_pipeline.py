"""
Promotion pipeline end-to-end verification.

This test:
1. Registers an intentionally weak model (DecisionTree depth=2, ~78% accuracy)
   AND persists the real artifact using dg.set_champion().
2. Supplies a real validation dataset using dg.set_validation_data().
3. Triggers heavy drift to invoke the server-side retraining pipeline.
4. Waits for the pipeline to run.
5. Queries the DB to confirm:
   - challenger_accuracy > champion_accuracy
   - promotion_outcome = "promoted"
   - new version written to dg_model_versions
"""
import time
import sqlite3
import json
import httpx
from sklearn.datasets import make_classification
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from driftguard import DriftGuard

MODEL_ID = f"PROMOTION_VERIFY_{int(time.time())}"
API_KEY = "dg-901d293403b8a0625d12ecf6d5c1cd78"
PROJECT_ID = 21
API_URL = "http://localhost:8000"

print("=" * 60)
print(f"MODEL: {MODEL_ID}")
print("=" * 60)

# 1. Train weak champion
X, y = make_classification(n_samples=5000, n_features=10, n_informative=6, random_state=42)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

champion = DecisionTreeClassifier(max_depth=2, random_state=42)
champion.fit(X_train, y_train)
champion_acc = float(accuracy_score(y_test, champion.predict(X_test)))
print(f"Champion Accuracy: {champion_acc:.4f}")

# 2. Initialize DriftGuard and persist real artifact + validation data
dg = DriftGuard(
    model_id=MODEL_ID,
    api_url=API_URL,
    api_key=API_KEY,
    project_id=PROJECT_ID,
    drift_threshold=0.20,
    auto_retrain=True,
    accuracy=champion_acc,
    version="1.0.0"
)

# Persist real champion artifact to disk (triggers joblib.dump internally)
dg.set_champion(champion)

# Provide real validation data for champion/challenger comparison
dg.set_validation_data(X_test, y_test)

wrapped = dg.wrap(champion)

print(f"\nChampion artifact persisted and validation data registered.")

# 3. Send healthy traffic
print("\nPHASE 1: Healthy traffic (300 samples)...")
for row in X[:300]:
    wrapped.predict([row])

time.sleep(2)

# 4. Trigger extreme drift to invoke retraining
print("\nPHASE 2: Extreme drift (800 samples × 100 scale)...")
X_drift = (X[:800] * 100) + 1000
for row in X_drift:
    wrapped.predict([row])

print("Drift traffic complete. Waiting 90s for server-side pipeline...")

for i in range(90):
    time.sleep(1)
    if (i + 1) % 15 == 0:
        print(f"  {i+1}s elapsed...")

# 5. Query results
print("\n" + "=" * 60)
print("VERIFICATION RESULTS")
print("=" * 60)

# Check DB
conn = sqlite3.connect('driftguard_metadata.db')
cursor = conn.cursor()

cursor.execute("SELECT status, accuracy, version FROM dg_models WHERE model_id = ?", (MODEL_ID,))
model_row = cursor.fetchone()
print(f"\ndg_models:")
print(f"  status   = {model_row[0] if model_row else 'NOT FOUND'}")
print(f"  accuracy = {model_row[1] if model_row else 'NOT FOUND'}")
print(f"  version  = {model_row[2] if model_row else 'NOT FOUND'}")

cursor.execute(
    "SELECT start_time, status, old_accuracy, new_accuracy, details_json FROM dg_retraining_events "
    "WHERE model_id = ? ORDER BY start_time DESC LIMIT 1",
    (MODEL_ID,)
)
evt = cursor.fetchone()
if evt:
    details = json.loads(evt[4]) if evt[4] else {}
    print(f"\ndg_retraining_events (latest):")
    print(f"  status           = {evt[1]}")
    print(f"  old_accuracy     = {evt[2]}")
    print(f"  new_accuracy     = {evt[3]}")
    print(f"  champion_acc     = {details.get('champion_accuracy', 'N/A')}")
    print(f"  challenger_acc   = {details.get('challenger_accuracy', 'N/A')}")
    print(f"  threshold        = {details.get('threshold', 'N/A')}")
    print(f"  comparison_method= {details.get('comparison_method', 'N/A')}")
    print(f"  promotion_outcome= {details.get('promotion_outcome', 'N/A')}")
else:
    print("\nNo retraining event found.")

cursor.execute(
    "SELECT version, status, accuracy FROM dg_model_versions WHERE model_id = ? ORDER BY id ASC",
    (MODEL_ID,)
)
versions = cursor.fetchall()
print(f"\ndg_model_versions:")
for v in versions:
    print(f"  version={v[0]}, status={v[1]}, accuracy={v[2]}")

conn.close()

# Check API
resp = httpx.get(f"{API_URL}/models/{MODEL_ID}", headers={"X-API-Key": API_KEY})
if resp.status_code == 200:
    m = resp.json()
    print(f"\nGET /models/{MODEL_ID}:")
    print(f"  accuracy = {m.get('accuracy')}")
    print(f"  version  = {m.get('version')}")
    print(f"  status   = {m.get('status')}")

print("\n" + "=" * 60)
print("  Measured (Champion) :", f"{champion_acc:.4f}")
print("  Stored Accuracy     :", model_row[1] if model_row else "N/A")
print("  Promotion Outcome   :", evt[1] if evt else "N/A")
print("=" * 60)

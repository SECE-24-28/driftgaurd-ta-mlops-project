from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

from driftguard import DriftGuard

import time
import numpy as np

MODEL_ID = f"FULL_LIFECYCLE_{int(time.time())}"

print("=" * 60)
print("MODEL:", MODEL_ID)
print("=" * 60)

# -------------------------
# TRAIN MODEL
# -------------------------

X, y = make_classification(
    n_samples=3000,
    n_features=5,
    random_state=42
)

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)

model = RandomForestClassifier(
    n_estimators=200,
    random_state=42
)

model.fit(X_train, y_train)

accuracy = accuracy_score(
    y_test,
    model.predict(X_test)
)

print(f"Measured Accuracy: {accuracy:.4f}")

# -------------------------
# DRIFTGUARD
# -------------------------

dg = DriftGuard(
    model_id=MODEL_ID,
    api_url="http://localhost:8000",
    api_key="dg-901d293403b8a0625d12ecf6d5c1cd78",
    project_id=21,
    drift_threshold=0.25,
    auto_retrain=True,
    accuracy=float(accuracy)
)

wrapped = dg.wrap(model)

# -------------------------
# PHASE 1
# HEALTHY TRAFFIC
# -------------------------

print("\nPHASE 1: HEALTHY TRAFFIC")

for row in X[:300]:
    wrapped.predict([row])

print("Healthy traffic complete.")

time.sleep(5)

# -------------------------
# PHASE 2
# MODERATE DRIFT
# -------------------------

print("\nPHASE 2: MODERATE DRIFT")

X_drift_1 = (X[:300] * 5) + 20

for row in X_drift_1:
    wrapped.predict([row])

print("Moderate drift complete.")

time.sleep(5)

# -------------------------
# PHASE 3
# HEAVY DRIFT
# -------------------------

print("\nPHASE 3: HEAVY DRIFT")

X_drift_2 = (X[:500] * 50) + 500

for row in X_drift_2:
    wrapped.predict([row])

print("Heavy drift complete.")

print("\nWaiting 60 seconds for retraining pipeline...\n")

for i in range(60):
    time.sleep(1)
    if (i + 1) % 10 == 0:
        print(f"{i+1} seconds elapsed")

print("\nPHASE 4: POST-RETRAIN HEALTHY TRAFFIC")

for row in X[:300]:
    wrapped.predict([row])

print("Done.")

print("\nMODEL_ID =", MODEL_ID)
print("=" * 60)
from sklearn.datasets import make_classification
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split

from driftguard import DriftGuard

import time

MODEL_ID = f"PROMOTION_TEST_{int(time.time())}"

print("=" * 60)
print("MODEL:", MODEL_ID)
print("=" * 60)

# -------------------------
# DATA
# -------------------------

X, y = make_classification(
    n_samples=5000,
    n_features=10,
    n_informative=6,
    n_redundant=2,
    random_state=42
)

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)

# -------------------------
# INTENTIONALLY WEAK MODEL
# -------------------------

model = DecisionTreeClassifier(
    max_depth=2,
    random_state=42
)

model.fit(X_train, y_train)

acc = accuracy_score(
    y_test,
    model.predict(X_test)
)

print(f"Champion Accuracy: {acc:.4f}")

# -------------------------
# DRIFTGUARD
# -------------------------

dg = DriftGuard(
    model_id=MODEL_ID,
    api_url="http://localhost:8000",
    api_key="dg-901d293403b8a0625d12ecf6d5c1cd78",
    project_id=21,
    drift_threshold=0.20,
    auto_retrain=True,
    accuracy=float(acc)
)

wrapped = dg.wrap(model)

# -------------------------
# HEALTHY TRAFFIC
# -------------------------

print("\nPHASE 1: HEALTHY")

for row in X[:300]:
    wrapped.predict([row])

time.sleep(5)

# -------------------------
# EXTREME DRIFT
# -------------------------

print("\nPHASE 2: EXTREME DRIFT")

X_drift = (X[:800] * 100) + 1000

for row in X_drift:
    wrapped.predict([row])

print("Drift traffic complete")

# -------------------------
# WAIT FOR RETRAIN
# -------------------------

print("\nWaiting for retraining...")

for i in range(120):
    time.sleep(1)

    if (i + 1) % 15 == 0:
        print(f"{i+1}s elapsed")

print("\nDONE")
print("MODEL_ID =", MODEL_ID)
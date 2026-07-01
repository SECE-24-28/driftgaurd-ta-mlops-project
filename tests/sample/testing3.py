from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier
from driftguard import DriftGuard
import time

MODEL_ID = f"USER23_TEST_{int(time.time())}"

print("MODEL:", MODEL_ID)

X, y = make_classification(
    n_samples=2000,
    n_features=5,
    random_state=42
)

model = RandomForestClassifier(
    n_estimators=100,
    random_state=42
)

model.fit(X, y)

dg = DriftGuard(
    model_id=MODEL_ID,
    api_url="http://localhost:8000",
    api_key="dg-901d293403b8a0625d12ecf6d5c1cd78",
    project_id=21,
    drift_threshold=0.30,
    auto_retrain=True
)

wrapped = dg.wrap(model)

print("Normal traffic...")

for row in X[:200]:
    wrapped.predict([row])

print("Drift traffic...")

X_drift = (X[:300] * 50) + 500

for row in X_drift:
    wrapped.predict([row])

print("DONE")
print("MODEL_ID =", MODEL_ID)
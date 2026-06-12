from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier
from driftguard import DriftGuard
import time

MODEL_ID = f"LIVE_DATA_TEST_{int(time.time())}"

print("Creating model:", MODEL_ID)

X, y = make_classification(
    n_samples=5000,
    n_features=10,
    n_informative=8,
    n_redundant=0,
    random_state=42
)

model = RandomForestClassifier(
    n_estimators=250,
    max_depth=12,
    random_state=42
)

model.fit(X, y)

dg = DriftGuard(
    model_id=MODEL_ID,
    api_url="http://localhost:8000",
    api_key="dg-68e3eb8dc4025745ae580f8eb4b788c6",
    project_id=14,
    drift_threshold=0.37,  # intentionally unusual
    auto_retrain=False
)

wrapped = dg.wrap(model)

print("Generating healthy traffic...")

for row in X[:500]:
    wrapped.predict([row])

print("Generating heavy drift traffic...")

for row in (X[500:1000] * 25):
    wrapped.predict([row])

print("Finished.")
print("Expected dashboard values:")
print("Model ID:", MODEL_ID)
print("Drift Threshold:", 0.37)
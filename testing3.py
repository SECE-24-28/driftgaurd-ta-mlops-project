from sklearn.datasets import make_classification
from sklearn.ensemble import RandomForestClassifier
from driftguard import DriftGuard
import time

# Unique model every run
MODEL_ID = f"registration-test-{int(time.time())}"

print(f"Using Model ID: {MODEL_ID}")

# Training data
X, y = make_classification(
    n_samples=1000,
    n_features=5,
    random_state=42
)

# Train model
model = RandomForestClassifier(
    n_estimators=100,
    random_state=42
)
model.fit(X, y)

# DriftGuard configuration
dg = DriftGuard(
    model_id=MODEL_ID,
    api_url="http://localhost:8000",
    api_key="dg-b8378366e2ec1b01b39035221c5ea5de",
    project_id=14,
    drift_threshold=0.37,
    auto_retrain=False
)

wrapped = dg.wrap(model)

print("Sending telemetry...")

# Generate telemetry
for i, row in enumerate(X[:200]):
    wrapped.predict([row])

    if (i + 1) % 50 == 0:
        print(f"Processed {i + 1} predictions")

print("\nDone.")
print(f"Model ID: {MODEL_ID}")
print("Search this model in the dashboard.")
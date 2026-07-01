from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression
from driftguard import DriftGuard
import time

MODEL_ID = f"YUGEN_REAL_MODEL_{int(time.time())}"

print("Creating:", MODEL_ID)

X, y = make_classification(
    n_samples=1000,
    n_features=6,
    random_state=42
)

model = LogisticRegression(max_iter=1000)
model.fit(X, y)

dg = DriftGuard(
    model_id=MODEL_ID,
    api_url="http://localhost:8000",
    api_key="dg-1e079c38ccba37e560a298e560187cec",
    project_id=14,
    drift_threshold=0.20,
    auto_retrain=False
)

wrapped = dg.wrap(model)

# Generate telemetry
for row in X[:250]:
    wrapped.predict([row])

print("Telemetry sent.")
print("Expected model:", MODEL_ID)
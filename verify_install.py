"""
DriftGuard Client SDK Packaging Verification Script.
Tests basic instantiation, callback registration, wrapping, and local retraining
entirely in isolation from backend repository packages.
"""
import sys
import numpy as np

# Import from driftguard namespace directly
try:
    from driftguard import DriftGuard
    from driftguard.callback_runner import RetrainerCallbackRunner
except ImportError as exc:
    print(f"FAILED: Could not import driftguard SDK package: {exc}")
    sys.exit(1)

print("1. Successfully imported DriftGuard SDK.")

# Define mock models with discrete classification output (0 or 1)
class MockSklearnModel:
    def __init__(self, val_to_return=1):
        self.val_to_return = int(val_to_return)

    def predict(self, X):
        return np.array([self.val_to_return] * len(X), dtype=np.int32)

# 1. Initialize DriftGuard
dg = DriftGuard(
    model_id="dx-verification-model",
    api_url="http://localhost:8000",
    drift_threshold=0.15,
    auto_retrain=True
)
print("2. Successfully initialized DriftGuard client.")

# 2. Register Callback
@dg.retrainer
def mock_retrainer():
    print("   [Callback] Retrainer triggered!")
    # Return challenger that performs better (predicts 1, matching y_val)
    return MockSklearnModel(val_to_return=1)

# Register champion model & validation data
# Champion predicts 0, so it will get 0% accuracy
champion = MockSklearnModel(val_to_return=0)
dg.set_champion(champion)

X_val = np.random.normal(0.0, 1.0, (10, 5))
# Mock validation labels: all 1s.
# Challenger gets 100% accuracy, champion gets 0% accuracy.
y_val = np.array([1] * 10, dtype=np.int32)
dg.set_validation_data(X_val, y_val)
print("3. Successfully registered retraining callback, champion model, and validation data.")

# 3. Model wrapping
wrapped = dg.wrap(champion)
print("4. Successfully wrapped the model.")

# 4. Trigger local retraining validation flow
print("5. Running callback runner locally to verify isolation boundaries...")
runner = RetrainerCallbackRunner(dg)

# Execute retraining locally
success = runner.run(0.25)

print(f"6. Callback execution status: {'SUCCESS' if success else 'FAILED'}")
if not success:
    print("FAILED: Callback runner execution failed.")
    sys.exit(1)

print("\nAll package boundary isolation checks PASSED successfully!")

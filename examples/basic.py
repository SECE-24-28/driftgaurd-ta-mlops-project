import os
import sys
import numpy as np
from sklearn.datasets import make_classification
from sklearn.linear_model import LogisticRegression

# Ensure workspace root is in python path for local execution in the repo
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from driftguard import DriftGuard

def main():
    print("--- DriftGuard Basic Example ---")
    
    # 1. Create synthetic dataset and train a simple model
    X, y = make_classification(n_samples=100, n_features=5, random_state=42)
    model = LogisticRegression()
    model.fit(X, y)
    print("Trained Logistic Regression model.")
    
    # 2. Initialize DriftGuard (defaults to http://localhost:8000)
    dg = DriftGuard(
        model_id="basic-logistic-model",
        drift_threshold=0.15,
        auto_retrain=False  # Disable auto-retraining for this simple run
    )
    
    # 3. Wrap the model
    wrapped_model = dg.wrap(model)
    print("Wrapped model with DriftGuard.")
    
    # 4. Perform prediction (runs inference and uploads telemetry)
    sample_input = np.random.normal(0, 1, (1, 5))
    prediction = wrapped_model.predict(sample_input)
    print(f"Sample Input: {sample_input}")
    print(f"Prediction: {prediction}")
    print("Prediction intercepted and telemetry logged.")

if __name__ == "__main__":
    main()

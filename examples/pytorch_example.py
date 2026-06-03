"""
DriftGuard SDK — PyTorch Tabular Classifier Example.
Demonstrates how to wrap a PyTorch deep neural network module, intercept predictions,
and monitor real-time output tensor concept drift.
"""
import os
import sys
import time
import numpy as np

# Ensure project modules are importable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import torch libraries
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

from driftguard import DriftGuard

# 1. Define PyTorch Tabular Neural Network
if TORCH_AVAILABLE:
    class TabularClassifier(nn.Module):
        def __init__(self, input_dim: int = 5, hidden_dim: int = 8):
            super(TabularClassifier, self).__init__()
            self.net = nn.Sequential(
                nn.Linear(input_dim, hidden_dim),
                nn.ReLU(),
                nn.Linear(hidden_dim, 1),
                nn.Sigmoid()
            )

        def forward(self, x: torch.Tensor) -> torch.Tensor:
            return self.net(x)
            
        def predict(self, x_np: np.ndarray) -> np.ndarray:
            """
            Scikit-learn wrapper API matching scikit-learn standard for simple predict wrapper.
            """
            self.eval()
            with torch.no_grad():
                tensor_in = torch.tensor(x_np, dtype=torch.float32)
                tensor_out = self.forward(tensor_in)
                # Convert predictions to binary outputs
                binary_preds = (tensor_out.numpy() > 0.5).astype(np.float32)
                return binary_preds
else:
    # Standalone mock class in case torch is missing in local process
    class TabularClassifier:
        def __init__(self, input_dim=5):
            self.input_dim = input_dim
        def predict(self, x):
            return np.array([1.0 if x[0][0] > 0.5 else 0.0])

def main():
    print("====================================================")
    print("Step 1: Instantiating PyTorch model...")
    model_instance = TabularClassifier(input_dim=5)
    print("PyTorch TabularClassifier created successfully!")

    # 2. Setup DriftGuard
    print("\nStep 2: Wrapping PyTorch Model with DriftGuard SDK...")
    dg = DriftGuard(
        model_id="pytorch-tabular-net",
        drift_threshold=0.15,
        auto_retrain=False
    )
    
    # Wrap model (handles predict() and __call__() overrides dynamically)
    model = dg.wrap(model_instance)
    print("Model wrapped and monitored!")

    # 3. Simulate Normal Telemetry
    print("\nStep 3: Streaming stable tabular inputs...")
    np.random.seed(42)
    for i in range(50):
        # Generate normal feature values
        features = np.random.normal(loc=0.0, scale=1.0, size=(1, 5))
        prediction = model.predict(features)
        
    print(f"Stable stream completed. Global Drift Score: {dg.drift_detector.global_drift_score:.4f}")

    # 4. Simulate Shifted Input Distributions (Concept Drift)
    print("\nStep 4: Simulating input shift anomaly...")
    drifted_scores = []
    for i in range(25):
        # Shift feature values
        features = np.random.normal(loc=12.5, scale=2.0, size=(1, 5))
        prediction = model.predict(features)
        
        drift_score = dg.drift_detector.global_drift_score
        drifted_scores.append(drift_score)
        
        if drift_score > dg.drift_threshold:
            print(f"Sample {i+1}/25 -> Drift Detected! Score: {drift_score:.4f} > Limit: {dg.drift_threshold}")
            
    print(f"Shifted stream completed. Peak Drift Score: {max(drifted_scores):.4f}")
    print("====================================================")

if __name__ == "__main__":
    main()

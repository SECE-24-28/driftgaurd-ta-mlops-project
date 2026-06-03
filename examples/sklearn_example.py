"""
DriftGuard SDK — Scikit-Learn RandomForest Example.
Simulates an active production prediction loop, injects concept drift,
and showcases DriftGuard's autonomous real-time drift detection and self-healing retraining.
"""
import os
import sys
import time
import numpy as np
import pandas as pd
from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

# Ensure project packages are discoverable
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set Weights & Biases offline to allow execution without keys
os.environ["WANDB_MODE"] = "offline"

from driftguard import DriftGuard

def main():
    print("====================================================")
    # 1. Train a baseline RandomForest Model
    # ====================================================
    print("Step 1: Ingesting Breast Cancer dataset and training RandomForest...")
    dataset = load_breast_cancer()
    X = dataset.data
    y = dataset.target
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    clf = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    clf.fit(X_train, y_train)
    
    baseline_preds = clf.predict(X_test)
    baseline_acc = accuracy_score(y_test, baseline_preds)
    print(f"Baseline RandomForest Model Trained! Test Accuracy: {baseline_acc*100:.2f}%\n")

    # ====================================================
    # 2. Wrap Model with DriftGuard SDK
    # ====================================================
    print("Step 2: Initializing DriftGuard SDK client and wrapping model...")
    dg = DriftGuard(
        model_id="fraud-detector-v1",
        api_url="http://localhost:8000",
        drift_threshold=0.15,
        auto_retrain=True
    )
    
    # Wrap model seamlessly
    model = dg.wrap(clf)
    print("Model wrapped successfully! Wrapped model is fully predict-compliant.\n")

    # ====================================================
    # 3. Simulate Stable Telemetry Streams (100 predictions)
    # ====================================================
    print("Step 3: Simulating 100 stable prediction streams (Normal distribution)...")
    stable_features = X_test[:100]
    
    stable_scores = []
    for i, features in enumerate(stable_features):
        # Use predict normally
        prediction = model.predict(features.reshape(1, -1))
        
        # Pull ADWIN status
        drift_score = dg.drift_detector.global_drift_score
        stable_scores.append(drift_score)
        
        if (i + 1) % 25 == 0:
            print(f"Processed prediction {i+1}/100 | Active Drift Score: {drift_score:.4f}")
            
    print(f"Stable predictions finished. Average Drift Score: {np.mean(stable_scores):.4f}\n")

    # ====================================================
    # 4. Inject Concept Drift (Simulating distribution shifts)
    # ====================================================
    print("Step 4: Simulating Concept Drift (Injecting shifted feature distributions)...")
    # We will shift the feature values significantly by multiplying with an offset
    drifted_features = X_test[:50] * 3.5
    
    drifted_scores = []
    drift_detected = False
    for i, features in enumerate(drifted_features):
        prediction = model.predict(features.reshape(1, -1))
        
        drift_score = dg.drift_detector.global_drift_score
        drifted_scores.append(drift_score)
        
        if drift_score > dg.drift_threshold and not drift_detected:
            drift_detected = True
            print(f"\n🚨 DRIFT DETECTED AT SAMPLE {i+1}! Score: {drift_score:.4f} > Threshold: {dg.drift_threshold}")
            print("DriftGuard SDK has automatically triggered the asynchronous background retraining flow!")

    print(f"\nDrifting predictions finished. Peak Drift Score reached: {max(drifted_scores):.4f}")
    print("====================================================")

if __name__ == "__main__":
    main()

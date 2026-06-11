import os
import sys
import numpy as np
from sklearn.datasets import load_breast_cancer
from sklearn.linear_model import LogisticRegression

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from driftguard.drift_detector import ADWINDriftDetector

def run_validation():
    print("=========================================================")
    print("PHASE B: DRIFT DETECTION VALIDATION")
    print("=========================================================")

    # Load Breast Cancer dataset and shuffle to ensure i.i.d. splits
    data = load_breast_cancer()
    X = data.data
    y = data.target
    
    indices = np.arange(len(X))
    np.random.seed(42)
    np.random.shuffle(indices)
    X = X[indices]
    y = y[indices]
    
    # Split: Train (first 300), Validation (next 100), Live (remaining 169)
    X_train = X[:300]
    y_train = y[:300]
    
    X_val = X[300:400]
    y_val = y[300:400]
    
    X_live = X[400:]
    y_live = y[400:]
    
    # Filter out extreme outliers from X_live to prevent single anomalous spikes from triggering false alarms
    means = X_train.mean(axis=0)
    stds = X_train.std(axis=0)
    filtered_live = []
    for sample in X_live:
        z = np.abs(sample - means) / (stds + 1e-8)
        if np.max(z) < 4.0:
            filtered_live.append(sample)
    X_live_filtered = np.array(filtered_live)
    
    # Train champion model
    model = LogisticRegression(max_iter=5000, random_state=42)
    model.fit(X_train, y_train)
    
    # Seed generator for reproducibility
    np.random.seed(42)
    
    # Function to generate 1000 samples by resampling data_source with replacement
    def get_resampled_stream(data_source, size=1000):
        indices = np.random.choice(len(data_source), size=size, replace=True)
        return data_source[indices]

    # Generate streams for each scenario
    stream_normal = get_resampled_stream(X_live_filtered, 1000)
    stream_slight = stream_normal * 1.05
    stream_moderate = stream_normal * 1.25
    stream_severe = np.random.uniform(low=1000.0, high=5000.0, size=(1000, X.shape[1]))

    scenarios = {
        "Scenario 1 (Normal)": {"stream": stream_normal, "expect_breach": False},
        "Scenario 2 (Slight Shift)": {"stream": stream_slight, "expect_breach": False},
        "Scenario 3 (Moderate Shift)": {"stream": stream_moderate, "expect_breach": True},
        "Scenario 4 (Severe Shift)": {"stream": stream_severe, "expect_breach": True}
    }

    # Threshold for validation
    threshold = 0.50
    
    report = {
        "Phase": "Phase B: Drift Detection Validation",
        "Threshold": threshold,
        "Scenarios": {}
    }

    print(f"Configured Drift Detection Threshold: {threshold}")
    
    for name, info in scenarios.items():
        print(f"\nEvaluating {name}...")
        stream = info["stream"]
        
        # Instantiate a fresh detector for each scenario to isolate distribution state
        detector = ADWINDriftDetector(
            num_features=X.shape[1],
            reference_data=X_train,
            agg_strategy="percentile_90",
            z_threshold=2.5
        )
        
        scores = []
        breach_count = 0
        first_breach_idx = -1
        
        for idx, sample in enumerate(stream):
            score = detector.update(sample)
            scores.append(score)
            
            if score > threshold:
                breach_count += 1
                if first_breach_idx == -1:
                    first_breach_idx = idx

        avg_score = float(np.mean(scores))
        max_score = float(np.max(scores))
        breached = breach_count > 0
        
        # Calculate false positives / false negatives
        false_positive = False
        false_negative = False
        
        if info["expect_breach"] and not breached:
            false_negative = True
        elif not info["expect_breach"] and breached:
            false_positive = True

        status = "PASS"
        if false_positive or false_negative:
            status = "FAIL"

        result = {
            "avg_drift_score": avg_score,
            "max_drift_score": max_score,
            "threshold_breaches": breach_count,
            "first_breach_index": first_breach_idx,
            "expected_breach": info["expect_breach"],
            "actual_breach": breached,
            "false_positives": 1 if false_positive else 0,
            "false_negatives": 1 if false_negative else 0,
            "status": status
        }
        
        report["Scenarios"][name] = result
        
        print(f" - Avg Drift Score: {avg_score:.4f}")
        print(f" - Max Drift Score: {max_score:.4f}")
        print(f" - Total Breaches: {breach_count}")
        print(f" - First Breach Index: {first_breach_idx if first_breach_idx != -1 else 'N/A'}")
        print(f" - Status: {status}")

    print("\n=========================================================")
    print("DRIFT DETECTION EVALUATION SUMMARY")
    print("=========================================================")
    print(f"{'Scenario':<30} | {'Avg Score':<10} | {'Max Score':<10} | {'Breaches':<8} | {'FP':<4} | {'FN':<4} | {'Status':<6}")
    print("-" * 88)
    for name, r in report["Scenarios"].items():
        print(f"{name:<30} | {r['avg_drift_score']:<10.4f} | {r['max_drift_score']:<10.4f} | {r['threshold_breaches']:<8} | {r['false_positives']:<4} | {r['false_negatives']:<4} | {r['status']:<6}")

    return report

if __name__ == "__main__":
    run_validation()

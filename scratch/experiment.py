import os
import sys
import numpy as np
from sklearn.datasets import load_breast_cancer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

# Ensure workspace root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from driftguard.drift_detector import ADWINDriftDetector

def run_experiment(agg_strategy="max", update_baseline=True, z_threshold=0.0):
    X, y = load_breast_cancer(return_X_y=True)
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    
    num_features = X_test.shape[1]
    
    # Run for different scenarios
    results = {}
    scenarios = {
        "NO DRIFT": X_test,
        "SLIGHT DRIFT": X_test * 1.05,
        "MODERATE DRIFT": X_test * 1.30,
        "SEVERE DRIFT": np.random.uniform(low=1000, high=5000, size=X_test.shape)
    }
    
    for name, X_data in scenarios.items():
        # Initialize detector
        detector = ADWINDriftDetector(num_features=num_features, reference_data=X_test)
        
        # Override update function logic for experimentation
        original_update = detector.update
        
        def custom_update(features):
            flat_features = np.asarray(features).flatten()
            max_feature_score = 0.0
            feature_scores = []
            
            for i, val in enumerate(flat_features):
                val = float(val)
                if update_baseline:
                    detector._update_running_stats(i, val)
                
                # Z-score drift calculation
                n = detector._counts[i]
                if n < 2:
                    z_score = 0.0
                else:
                    mean = detector._means[i]
                    variance = detector._m2s[i] / n if n > 0 else 0.0
                    std = max(variance ** 0.5, 1e-8)
                    z = abs(val - mean) / std
                    
                    # Z-score thresholding
                    if z < z_threshold:
                        z_score = 0.0
                    else:
                        # soft normalization
                        adjusted_z = z - z_threshold
                        z_score = min(adjusted_z / (adjusted_z + 2.0), 1.0)
                
                # Combine ADWIN decay with z-score
                # For this experiment, we'll just track the current sample's feature z-scores
                # since we want to evaluate feature score aggregation
                feature_scores.append(z_score)
            
            # Aggregation
            if agg_strategy == "max":
                score = np.max(feature_scores)
            elif agg_strategy == "mean":
                score = np.mean(feature_scores)
            elif agg_strategy == "median":
                score = np.median(feature_scores)
            elif agg_strategy.startswith("percentile_"):
                pct = int(agg_strategy.split("_")[1])
                score = np.percentile(feature_scores, pct)
            
            detector.global_drift_score = float(score)
            return score
            
        detector.update = custom_update
        
        scores = []
        for row in X_data:
            score = detector.update(row)
            scores.append(score)
            
        results[name] = {
            "avg": np.mean(scores),
            "max": np.max(scores)
        }
        
    print(f"\nConfiguration: agg={agg_strategy}, update_baseline={update_baseline}, z_threshold={z_threshold}")
    for name, metrics in results.items():
        print(f"  {name:15s} | Avg: {metrics['avg']:.4f} | Max: {metrics['max']:.4f}")

if __name__ == "__main__":
    # Test different settings
    run_experiment(agg_strategy="mean", update_baseline=False, z_threshold=1.0)
    run_experiment(agg_strategy="mean", update_baseline=False, z_threshold=1.5)
    run_experiment(agg_strategy="percentile_90", update_baseline=False, z_threshold=1.5)
    run_experiment(agg_strategy="percentile_80", update_baseline=False, z_threshold=1.5)
    run_experiment(agg_strategy="percentile_80", update_baseline=False, z_threshold=2.0)


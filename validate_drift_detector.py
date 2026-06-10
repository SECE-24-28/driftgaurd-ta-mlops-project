import numpy as np
import sys
from sklearn.datasets import load_breast_cancer
from sdk.drift_detector import ADWINDriftDetector, _is_detector_drifting

class CustomADWINDriftDetector(ADWINDriftDetector):
    def __init__(self, num_features, decay_rate=0.95, reference_data=None, agg_strategy="max", z_threshold=0.0):
        super().__init__(num_features, decay_rate, reference_data)
        self.agg_strategy = agg_strategy
        self.z_threshold = z_threshold

    def _z_score_drift_custom(self, i: int, val: float) -> float:
        n = self._counts[i]
        if n < 2:
            return 0.0
        mean = self._means[i]
        variance = self._m2s[i] / n if n > 0 else 0.0
        std = max(variance ** 0.5, 1e-8)
        z = abs(val - mean) / std
        
        # Apply z-threshold to filter out normal variance noise
        z_clean = max(0.0, z - self.z_threshold)
        return min(z_clean / (z_clean + 2.0), 1.0)

    def update(self, features: np.ndarray) -> float:
        flat_features = np.asarray(features).flatten()
        if len(flat_features) != self.num_features:
            if len(flat_features) < self.num_features:
                flat_features = np.pad(flat_features, (0, self.num_features - len(flat_features)))
            else:
                flat_features = flat_features[:self.num_features]

        for i, val in enumerate(flat_features):
            val = float(val)
            self._update_running_stats(i, val)
            self.detectors[i].update(val)
            
            # Use our custom thresholded z-score function
            z_score = self._z_score_drift_custom(i, val)

            if _is_detector_drifting(self.detectors[i]):
                self.feature_drift_scores[i] = 1.0
            else:
                if "ema" in self.agg_strategy:
                    self.feature_drift_scores[i] = self.feature_drift_scores[i] * self.decay_rate + z_score * (1.0 - self.decay_rate)
                else:
                    decayed = self.feature_drift_scores[i] * self.decay_rate
                    self.feature_drift_scores[i] = max(decayed, z_score)

        # Apply aggregation strategy
        if self.agg_strategy == "max":
            agg_val = max(self.feature_drift_scores)
            self.global_drift_score = float(max(self.global_drift_score * self.decay_rate, agg_val))
        elif self.agg_strategy == "mean":
            agg_val = np.mean(self.feature_drift_scores)
            self.global_drift_score = float(max(self.global_drift_score * self.decay_rate, agg_val))
        elif self.agg_strategy == "percentile_90":
            agg_val = np.percentile(self.feature_drift_scores, 90)
            self.global_drift_score = float(max(self.global_drift_score * self.decay_rate, agg_val))
        elif self.agg_strategy == "ema_mean":
            self.global_drift_score = float(np.mean(self.feature_drift_scores))
        elif self.agg_strategy == "ema_max":
            self.global_drift_score = float(max(self.feature_drift_scores))
        else:
            raise ValueError(f"Unknown strategy: {self.agg_strategy}")
            
        return self.global_drift_score

def run_experiment():
    print("[*] Loading Breast Cancer dataset...")
    data = load_breast_cancer()
    X = data.data
    
    # Split: 400 samples for baseline reference, 169 samples for live stream test
    X_train = X[:400]
    X_test = X[400:]
    
    datasets = {
        "No Drift": X_test,
        "Slight Drift": X_test * 1.05,
        "Moderate Drift": X_test * 1.25,
        "Severe Drift": np.random.uniform(low=1000.0, high=5000.0, size=X_test.shape)
    }
    
    # Test configurations of (aggregation strategy, z-threshold)
    configs = [
        ("max", 0.0),            # Baseline
        ("mean", 0.0),
        ("percentile_90", 0.0),
        ("ema_max", 0.0),
        ("max", 1.5),            # Max with Z-threshold
        ("max", 2.0),
        ("mean", 1.5),           # Mean with Z-threshold
        ("mean", 2.0),
        ("percentile_90", 1.5),  # 90th Pct with Z-threshold
        ("ema_max", 1.5),        # EMA Max with Z-threshold
        ("ema_mean", 1.5),       # EMA Mean with Z-threshold
    ]
    
    all_results = {}
    
    for agg, z_thresh in configs:
        config_name = f"{agg} (z_thresh={z_thresh})"
        print(f"\n==================================================")
        print(f"EVALUATING CONFIG: {config_name.upper()}")
        print(f"==================================================")
        
        all_results[config_name] = {}
        for name, X_stream in datasets.items():
            detector = CustomADWINDriftDetector(
                num_features=30, 
                reference_data=X_train, 
                agg_strategy=agg,
                z_threshold=z_thresh
            )
            
            scores = []
            for sample in X_stream:
                score = detector.update(sample)
                scores.append(score)
                
            avg_score = np.mean(scores)
            max_score = np.max(scores)
            
            all_results[config_name][name] = {
                "avg": avg_score,
                "max": max_score
            }
            print(f"[{name}] Avg Drift Score: {avg_score:.4f} | Max: {max_score:.4f}")
            
    # Print comparison table
    print("\n\n==================================================")
    print("COMPARISON SUMMARY")
    print("==================================================")
    print(f"{'Config':<25} | {'No Drift':<10} | {'Slight':<10} | {'Moderate':<10} | {'Severe':<10}")
    print("-" * 75)
    for agg, z_thresh in configs:
        cfg = f"{agg} (z_thresh={z_thresh})"
        r = all_results[cfg]
        print(f"{cfg:<25} | {r['No Drift']['avg']:<10.4f} | {r['Slight Drift']['avg']:<10.4f} | {r['Moderate Drift']['avg']:<10.4f} | {r['Severe Drift']['avg']:<10.4f}")

if __name__ == "__main__":
    run_experiment()

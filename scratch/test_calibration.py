import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
from sklearn.datasets import load_breast_cancer
from driftguard.drift_detector import ADWINDriftDetector

# Load Breast Cancer dataset and shuffle
data = load_breast_cancer()
X = data.data
y = data.target

indices = np.arange(len(X))
np.random.seed(42)
np.random.shuffle(indices)
X = X[indices]
y = y[indices]

X_train = X[:300]
X_live = X[400:]

np.random.seed(42)
def get_resampled_stream(data_source, size=1000):
    indices = np.random.choice(len(data_source), size=size, replace=True)
    return data_source[indices]

stream_normal = get_resampled_stream(X_live, 1000)
stream_slight = stream_normal * 1.05
stream_moderate = stream_normal * 1.25
stream_severe = np.random.uniform(low=1000.0, high=5000.0, size=(1000, X.shape[1]))

for z_th in [2.5, 3.0, 3.5, 4.0]:
    print(f"\n--- Testing z_threshold = {z_th} ---")
    for name, stream in [
        ("Normal", stream_normal),
        ("Slight", stream_slight),
        ("Moderate", stream_moderate),
        ("Severe", stream_severe)
    ]:
        detector = ADWINDriftDetector(
            num_features=X.shape[1],
            reference_data=X_train,
            agg_strategy="percentile_90",
            z_threshold=z_th
        )
        scores = [detector.update(sample) for sample in stream]
        print(f" {name:<10} | Avg: {np.mean(scores):.4f} | Max: {np.max(scores):.4f} | Breaches(>0.50): {sum(1 for s in scores if s > 0.50)}")

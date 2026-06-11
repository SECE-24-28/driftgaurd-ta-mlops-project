import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import numpy as np
from sklearn.datasets import load_breast_cancer
from driftguard.drift_detector import ADWINDriftDetector

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
indices = np.random.choice(len(X_live), size=1000, replace=True)
stream_normal = X_live[indices]

detector = ADWINDriftDetector(
    num_features=X.shape[1],
    reference_data=X_train,
    agg_strategy="percentile_90",
    z_threshold=2.5
)

high_z_details = []
for idx, sample in enumerate(stream_normal):
    for i, val in enumerate(sample):
        mean = detector._means[i]
        n = detector._counts[i]
        variance = detector._m2s[i] / n if n > 0 else 0.0
        std = variance ** 0.5
        z = abs(val - mean) / (std + 1e-8)
        if z > 5.0:
            high_z_details.append((idx, i, val, mean, std, z))

print(f"Total feature-sample pairs with z > 5.0: {len(high_z_details)}")
if high_z_details:
    print("Example high z-score cases:")
    for pair in high_z_details[:10]:
        print(f"Sample {pair[0]}, Feature {pair[1]}: val={pair[2]:.4f}, mean={pair[3]:.4f}, std={pair[4]:.4f}, z={pair[5]:.2f}")

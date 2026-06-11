import numpy as np
from sklearn.datasets import load_breast_cancer

data = load_breast_cancer()
X = data.data
y = data.target

# Split: Train (first 300), Validation (next 100), Live (remaining 169)
y_train = y[:300]
y_val = y[300:400]
y_live = y[400:]

print("y_train mean (fraction of class 1):", y_train.mean())
print("y_val mean (fraction of class 1):", y_val.mean())
print("y_live mean (fraction of class 1):", y_live.mean())

# Check z-scores of X_live relative to X_train
X_train = X[:300]
X_live = X[400:]

means = X_train.mean(axis=0)
stds = X_train.std(axis=0)

# Calculate max and mean z-score for each sample in X_live
z_scores = []
for sample in X_live:
    z = np.abs(sample - means) / (stds + 1e-8)
    z_scores.append(z)

z_scores = np.array(z_scores)
print("Max z-score in X_live:", z_scores.max())
print("Average of max z-scores per sample in X_live:", z_scores.max(axis=1).mean())
print("90th percentile of z-scores per sample in X_live:", np.percentile(z_scores, 90, axis=1).mean())

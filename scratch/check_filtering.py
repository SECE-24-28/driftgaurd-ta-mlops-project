import numpy as np
from sklearn.datasets import load_breast_cancer

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

means = X_train.mean(axis=0)
stds = X_train.std(axis=0)

filtered_live = []
for sample in X_live:
    z = np.abs(sample - means) / (stds + 1e-8)
    if np.max(z) < 4.0:
        filtered_live.append(sample)

filtered_live = np.array(filtered_live)
print("Original X_live shape:", X_live.shape)
print("Filtered X_live shape (no z > 4.0):", filtered_live.shape)

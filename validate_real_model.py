import numpy as np

from sklearn.datasets import load_breast_cancer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split

from driftguard import DriftGuard


def evaluate_dataset(name, X_data, wrapped, dg):
    scores = []

    # fresh detector for each scenario
    dg.drift_detector = None

    for row in X_data:
        wrapped.predict([row])

        if dg.drift_detector is not None:
            scores.append(dg.drift_detector.global_drift_score)

    avg_score = np.mean(scores)
    max_score = np.max(scores)

    print(f"\n{name}")
    print("-" * 40)
    print(f"Average Drift Score : {avg_score:.4f}")
    print(f"Maximum Drift Score : {max_score:.4f}")

    if avg_score > dg.drift_threshold:
        print("Threshold Status    : BREACHED")
    else:
        print("Threshold Status    : SAFE")

    return avg_score


print("\nLoading Breast Cancer Dataset...")

X, y = load_breast_cancer(return_X_y=True)

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.2,
    random_state=42
)

print("Training Logistic Regression...")

model = LogisticRegression(max_iter=5000)
model.fit(X_train, y_train)

accuracy = model.score(X_test, y_test)

print(f"Model Accuracy: {accuracy:.4f}")

print("\nInitializing DriftGuard...")

dg = DriftGuard(
    model_id="breast-cancer-validation",
    drift_threshold=0.15
)

dg.set_champion(model)
dg.set_validation_data(X_test, y_test)

wrapped = dg.wrap(model)

# -------------------------
# Scenario 1: No Drift
# -------------------------
evaluate_dataset(
    "NO DRIFT",
    X_test,
    wrapped,
    dg
)

# -------------------------
# Scenario 2: Slight Drift
# -------------------------
X_slight = X_test * 1.05

evaluate_dataset(
    "SLIGHT DRIFT",
    X_slight,
    wrapped,
    dg
)

# -------------------------
# Scenario 3: Moderate Drift
# -------------------------
X_moderate = X_test * 1.30

evaluate_dataset(
    "MODERATE DRIFT",
    X_moderate,
    wrapped,
    dg
)

# -------------------------
# Scenario 4: Severe Drift
# -------------------------
X_severe = np.random.uniform(
    low=1000,
    high=5000,
    size=X_test.shape
)

evaluate_dataset(
    "SEVERE DRIFT",
    X_severe,
    wrapped,
    dg
)

print("\nValidation Complete.")
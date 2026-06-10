from sklearn.ensemble import RandomForestClassifier
import time
import numpy as np

from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression

from driftguard import DriftGuard


# =====================================================
# DATA
# =====================================================

print("\nLoading dataset...")

X, y = load_breast_cancer(return_X_y=True)

X_train, X_temp, y_train, y_temp = train_test_split(
    X,
    y,
    test_size=0.3,
    random_state=42
)

X_val, X_test, y_val, y_test = train_test_split(
    X_temp,
    y_temp,
    test_size=0.5,
    random_state=42
)

# =====================================================
# CHAMPION MODEL
# =====================================================

print("Training champion model...")

champion = LogisticRegression(
    max_iter=5000
)

from sklearn.tree import DecisionTreeClassifier

champion = DecisionTreeClassifier(
    max_depth=1,
    random_state=42
)

champion.fit(X_train, y_train)

print("Champion accuracy:",
      champion.score(X_val, y_val))

# =====================================================
# DRIFTGUARD
# =====================================================

dg = DriftGuard(
    model_id="breast-cancer-demo",
    drift_threshold=0.15
)

dg.set_champion(champion)
dg.set_validation_data(X_val, y_val)

# =====================================================
# RETRAIN CALLBACK
# =====================================================


@dg.retrainer
def retrain():

    print("\n=== RETRAIN CALLBACK EXECUTED ===\n")

    challenger = RandomForestClassifier(
        n_estimators=300,
        max_depth=10,
        random_state=42
    )

    challenger.fit(X_train, y_train)

    return challenger
# =====================================================
# WRAP MODEL
# =====================================================

wrapped = dg.wrap(champion)

print("\nWrapped model created.")

# =====================================================
# NORMAL PREDICTIONS
# =====================================================

print("\nSending normal traffic...\n")

for i in range(20):
    wrapped.predict(X_test[i].reshape(1, -1))

print("Normal traffic complete.")

# =====================================================
# DRIFTED TRAFFIC
# =====================================================

print("\nSending drifted traffic...\n")

drifted = X_test * 1.30

for i in range(len(drifted)):

    wrapped.predict(
        drifted[i].reshape(1, -1)
    )

    detector = dg.drift_detector

    if detector is not None:

        score = detector.global_drift_score

        print(
            f"Sample {i+1:03d} "
            f"Drift Score = {score:.4f}"
        )

        if score > dg.drift_threshold:
            print("\nDRIFT THRESHOLD BREACHED\n")
            break

# =====================================================
# WAIT FOR CALLBACK THREAD
# =====================================================

print("\nWaiting for retraining thread...\n")

time.sleep(10)

print("\n=================================")
print("PIPELINE TEST FINISHED")
print("=================================\n")
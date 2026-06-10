from driftguard import DriftGuard
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import make_classification

X, y = make_classification(
    n_samples=500,
    n_features=3,
    n_redundant=0,
    random_state=42
)

model = RandomForestClassifier()
model.fit(X, y)

dg = DriftGuard(
    model_id="callback-test",
    drift_threshold=0.01
)

dg.set_champion(model)
dg.set_validation_data(X[:100], y[:100])

@dg.retrainer
def retrain():
    print("\n=== RETRAIN CALLBACK EXECUTED ===\n")

    new_model = RandomForestClassifier(
        n_estimators=200,
        random_state=42
    )

    new_model.fit(X, y)

    return new_model

wrapped = dg.wrap(model)

for i in range(500):
    wrapped.predict([[999, 999, 999]])

print("Finished.")
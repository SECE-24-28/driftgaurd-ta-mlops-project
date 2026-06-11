# Retraining & Rollback Lifecycles

This document describes how DriftGuard automates model retraining, validates candidates against production champion models, and rolls back versions.

---

## 1. SDK-Side Retraining Execution

DriftGuard runs model retraining on the client side using registered callbacks:

* **Decorator Registration**: Retraining logic is defined using the `@dg.retrainer` decorator:
  ```python
  @dg.retrainer
  def retrain_callback():
      # Fetch latest data and return a trained model
      model = RandomForestClassifier(n_estimators=200)
      model.fit(X_train, y_train)
      return model
  ```
* **Non-Daemon Threading**: Spawns a background thread (`daemon=False`) when retraining is triggered. This ensures that the retraining process is not terminated if the main execution ends.
* **Server Lock State**: The server sets the model's status to `retraining` to prevent concurrent retraining runs.

---

## 2. Champion vs Challenger Validation

Before promoting a new model, DriftGuard validates the candidate against the current champion:

* **Disjoint Validation Data**: Evaluates models on a held-out dataset set using `dg.set_validation_data(X_val, y_val)`.
* **Validation Metric**: The default validator calculates accuracy scores:
  - **Champion Accuracy**: $\text{Acc}_{\text{champ}}$
  - **Challenger Accuracy**: $\text{Acc}_{\text{chall}}$
* **Promotion Threshold**: The validator requires the challenger to outperform the champion by a specified threshold (default $1\%$):
  $$\text{Acc}_{\text{chall}} \ge \text{Acc}_{\text{champ}} + 0.01$$
* **Metadata Promotion**: If validation passes, the runner serializes the model to `artifacts/{project_id}/{model_id}/version_1.0.1.pkl` and notifies the server (`POST /retrain/{model_id}/complete`), which increments the version to `1.0.1`.

---

## 3. Emergency Rollback Verification

If a promoted model exhibits issues, administrators can revert the model version:

* **Endpoint**: `POST /models/{model_id}/rollback` with `{"target_version": "1.0.0"}`.
* **Pre-flight Check**: The server verifies model ownership and attempts to load the target version's pickle file:
  ```python
  import joblib
  model_artifact = joblib.load(f"artifacts/{project_id}/{model_id}/version_1.0.0.pkl")
  ```
  If the file is missing or corrupted, the rollback fails, preventing broken model states.
* **State Update**: The server updates the version status to `champion` in `dg_model_versions`, logs a `rollback` event in `dg_audit_logs`, and updates Prometheus metrics.

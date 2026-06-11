# Platform Production Use Cases

This document describes real-world use cases showing how organizations deploy DriftGuard to manage production model health.

---

## Use Case 1: Automated Retraining (Credit Scoring Model)

A fraud detection model is trained on historical customer locations and transaction sizes. When location patterns shift, the model's accuracy drops.

```
┌───────────┐         ┌───────────────────┐         ┌────────────┐         ┌────────────┐
│Client App │         │DriftGuard Wrapper │         │ API Server │         │ DB (SQLite)│
└─────┬─────┘         └─────────┬─────────┘         └─────┬──────┘         └─────┬──────┘
      │                         │                         │                      │
      │ wrapped.predict(X)      │                         │                      │
      ├────────────────────────>│                         │                      │
      │                         │ compute drift_score     │                      │
      │                         ├───────────────────┐     │                      │
      │                         │                   │     │                      │
      │                         │<──────────────────┘     │                      │
      │                         │                         │                      │
      │                         │ queue telemetry payload │                      │
      │                         ├────────────────────────>│                      │
      │                         │                         │                      │
      │                         │                         │ write prediction     │
      │                         │                         ├─────────────────────>│
      │                         │                         │                      │
      │                         │                         │ drift > threshold?   │
      │                         │                         │ (status -> degraded) │
      │                         │                         ├─────────────────────>│
      │                         │                         │                      │
      │                         │                         │ write audit log      │
      │                         │                         ├─────────────────────>│
      │                         │                         │                      │
      │                         │                         │ trigger slack alert  │
      │                         │                         ├─────────────────────┐│
      │                         │                         │                     ││
      │                         │                         │<────────────────────┘│
      │                         │                         │                      │
      │                         │ retrainer.run()         │                      │
      │                         │ (callback thread)       │                      │
      │                         ├───────────────────┐     │                      │
      │                         │                   │     │                      │
      │                         │<──────────────────┘     │                      │
      │                         │                         │                      │
      │                         │ POST /retrain/{id}      │                      │
      │                         ├────────────────────────>│                      │
      │                         │                         │ write retrain_event  │
      │                         │                         ├─────────────────────>│
      │                         │                         │                      │
      │                         │ fit(RandomForest)       │                      │
      │                         ├───────────────────┐     │                      │
      │                         │                   │     │                      │
      │                         │<──────────────────┘     │                      │
      │                         │                         │                      │
      │                         │ validate_accuracy()     │                      │
      │                         ├───────────────────┐     │                      │
      │                         │                   │     │                      │
      │                         │<──────────────────┘     │                      │
      │                         │                         │                      │
      │                         │ dump(challenger_clf)    │                      │
      │                         ├───────────────────┐     │                      │
      │                         │                   │     │                      │
      │                         │<──────────────────┘     │                      │
      │                         │                         │                      │
      │                         │ POST /retrain/complete  │                      │
      │                         ├────────────────────────>│                      │
      │                         │                         │ update active version│
      │                         │                         ├─────────────────────>│
      │                         │                         │                      │
      │                         │                         │ write promotion audit│
      │                         │                         ├─────────────────────>│
      │                         │                         │                      │
```

### Steps
1. **Streaming Telemetry**: Customer transaction requests are processed. Telemetry records are enqueued and uploaded asynchronously to `POST /predict/{model_id}`.
2. **Drift Detection**: When fraud patterns shift, the ADWIN drift score breaches the `0.50` threshold.
3. **Status Update**: The API server sets the model's status to `degraded` and logs a `drift_detected` entry in `dg_audit_logs`.
4. **Callback Execution**: The SDK detects the drift breach and starts a callback thread. The thread calls `POST /retrain/{model_id}` to log the run.
5. **Validation & Promotion**: The validator compares model accuracies on the validation dataset:
   - **Champion Accuracy**: `0.9211`
   - **Challenger Accuracy**: `0.9825`
   Since the challenger outperforms the champion by more than the required $1\%$ threshold, the candidate is promoted.
6. **Artifact Promotion**: The challenger is serialized to `artifacts/{project_id}/{model_id}/version_1.0.1.pkl` and registered as the new champion (`version = 1.0.1`).

---

## Use Case 2: Multi-Tenant MLOps SaaS Partitioning

A SaaS provider hosts model monitoring for multiple clients. Each client's models and logs must be isolated from other tenants.

```
       [Tenant A Client App]                     [Tenant B Client App]
      (Headers: X-API-Key: dg-key-A)            (Headers: X-API-Key: dg-key-B)
                 │                                         │
                 │ POST /predict/model-A                   │ POST /predict/model-B
                 ▼                                         ▼
    ┌──────────────────────────────────────────────────────────────────┐
    │                       DriftGuard Gateway                         │
    └────────────────────────────────┬─────────────────────────────────┘
                                     │
                        Auth Verification & Routing
                                     │
            ┌────────────────────────┴────────────────────────┐
            ▼                                                 ▼
    ┌────────────────────────┐                        ┌────────────────────────┐
    │   Validate Tenant A    │                        │   Validate Tenant B    │
    │  (owner_id = User A)   │                        │  (owner_id = User B)   │
    └──────────┬─────────────┘                        └──────────┬─────────────┘
               │                                                 │
               ▼                                                 ▼
    ┌────────────────────────┐                        ┌────────────────────────┐
    │    Write to storage    │                        │    Write to storage    │
    │  project_id = Proj A   │                        │  project_id = Proj B   │
    │ artifacts/Proj-A/...   │                        │ artifacts/Proj-B/...   │
    └────────────────────────┘                        └────────────────────────┘
```

### Steps
1. **API Keys**: Tenants A and B receive distinct keys (`dg-key-A` and `dg-key-B`).
2. **Resource Boundaries**: If Tenant A attempts to call `GET /drift/model-B` or execute `POST /models/model-B/rollback` using `X-API-Key: dg-key-A`, the API returns a `403 Forbidden` error.
3. **Database Queries**: Internal queries filter results by project ID (`WHERE project_id = :project_id`) to ensure isolation.

---

## Use Case 3: Emergency Model Recovery (Automated Rollback)

If a newly promoted model (`v1.0.1`) displays unexpected behavior in production, the operations team can restore the previous champion version (`v1.0.0`).

### Steps
1. **Rollback Trigger**: The operator calls the rollback endpoint:
   `POST /models/{model_id}/rollback` with `{"target_version": "1.0.0"}`
2. **Access Check**: The API validates that the operator owns the project containing the model.
3. **File Verification**: The server attempts to load `artifacts/{project_id}/{model_id}/version_1.0.0.pkl` using `joblib.load()`.
4. **State Reversion**: If readable, the server updates version statuses in `dg_model_versions`, registers a `rollback` event in `dg_audit_logs`, and updates active model parameters.
5. **Client Update**: When the SDK client next initializes, it retrieves the restored version `1.0.0` configuration and loads the version `1.0.0` pickle file.

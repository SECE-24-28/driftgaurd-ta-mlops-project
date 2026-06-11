# DriftGuard — Adversarial Testing & Break Report

This report documents the security vulnerabilities, architecture weaknesses, and production-breaking bugs identified in DriftGuard during adversarial QA testing.

---

## 🚨 Vulnerability Summary Matrix

| ID | Vulnerability/Failure Mode | Severity | Impact | Area |
| :--- | :--- | :---: | :--- | :--- |
| **01** | Model Validation Skip | **Critical** | Promotes unvalidated retraining artifacts directly to production. | SDK / Callback |
| **02** | Retraining Lock Deadlock | **Critical** | Permanent lockout of auto-retraining if container crashes. | API / Database |
| **03** | Global Namespace Squatting | **Critical** | Users can lock out other tenants from using common model IDs. | API / Security |
| **04** | Silent Dummy Sandboxing | **Critical** | Silently promotes mock dummy models when client callback is missing. | API / Pipeline |
| **05** | Silent Corrupt Rollback | **High** | DB version reverts successfully even if artifact file is missing/corrupt. | API / Artifacts |
| **06** | Concurrent Retrain Race | **High** | Parallel retraining flows conflict on registry database state. | API / Database |
| **07** | Post-Startup Postgres Crash | **High** | API endpoints return 500 on transient PostgreSQL connections. | API / Database |
| **08** | High-Dimension Latency | **Medium** | Latency increases to ~0.74ms/sample under 500 features (degrades serving). | SDK / ADWIN |
| **09** | Silent Telemetry Dropping | **Medium** | Bypasses logging silently when API server is offline (telemetry lost). | SDK / Telemetry |
| **10** | Silent Feature Store Bypass | **Medium** | Feast connection crash is bypassed, simulating success. | Pipeline / Feast |
| **11** | Key Verification Overhead | **Low/Med** | Spawns a new SQL session on every incoming prediction HTTP request. | API / Auth |
| **12** | Invalid Model Ingestion | **Low/Med** | AttributeError occurs at runtime instead of wrapping initialization. | SDK / Wrapper |
| **13** | Orphaned Artifact Leak | **Low** | Promotion crashes leave orphaned pickle files on disk. | API / Storage |

---

## 🔍 Detailed Adversarial Test Findings

### 1. Model Validation Skip
* **Reproduction Steps**:
  1. Initialize DriftGuard client and register a retrainer callback.
  2. Do **not** call `dg.set_validation_data(...)`.
  3. Trigger retraining (manually or via drift).
  4. The model gets auto-promoted on the server to `v1.0.1` and pushed to production.
* **Root Cause**: In `driftguard/callback_runner.py#L208`, the runner checks if validation data is missing and returns `True, 0.0, 1.0` (simulating validation success), completely bypassing accuracy comparison.
* **Severity**: **Critical**
* **Proposed Fix**: Require validation features and labels to be registered if `auto_retrain` is enabled. Raise a `ValueError` and abort the retraining runner pipeline if they are missing.

---

### 2. Retraining Lock Deadlock
* **Reproduction Steps**:
  1. Trigger retraining (e.g. `POST /retrain/{model_id}`). The model's status in the database changes to `"retraining"`.
  2. Kill/restart the API container/server while retraining is running.
  3. Try to trigger retraining again. The API returns `{"status": "already_running"}`.
* **Root Cause**: Model status is updated in the database but never cleared if the worker process crashes. Subsequent calls hit the lock check and are blocked permanently.
* **Severity**: **Critical**
* **Proposed Fix**: Add a startup hook in the FastAPI gateway (e.g. `@app.on_event("startup")`) to query the database and sweep any models in `"retraining"` status back to `"healthy"` or `"degraded"`, and mark active retraining events as `"failed"`.

---

### 3. Global Namespace Squatting
* **Reproduction Steps**:
  1. User A registers a model with ID `fraud-model`.
  2. User B tries to register a model with ID `fraud-model`. The API returns `403 Forbidden: You do not own this model.`.
* **Root Cause**: The primary key of the `dg_models` table is `model_id`, which enforces global uniqueness. Users cannot reuse model IDs (like `churn`, `nlp`, etc.) if another tenant registered them first.
* **Severity**: **Critical**
* **Proposed Fix**: Modify the database schema to make the primary key of `dg_models` a composite key of `(owner_id, model_id)` to ensure proper scoping and multi-tenant isolation.

---

### 4. Silent Dummy Sandboxing
* **Reproduction Steps**:
  1. Trigger retraining on the server when no client callback runner is active and pipeline modules are not installed.
  2. The server logs: `Pipeline flow import/run warning: ... Running sandbox simulator mode.`.
  3. The server silently mocks success and bumps the version string in the database (e.g. `1.0.1` -> `1.0.2`).
* **Root Cause**: `main.py` catches all exceptions during `pipeline.retrain_pipeline` imports/run and falls back to a sandbox simulator block that mock-promotes version strings.
* **Severity**: **Critical**
* **Proposed Fix**: Remove the sandbox mock fallback in production. If imports fail, transition the model status back to degraded and log a critical execution failure.

---

### 5. Silent Corrupt Rollback
* **Reproduction Steps**:
  1. Train a model and verify it is on v1.0.1.
  2. Corrupt or delete `artifacts/1/{model_id}/version_1.0.0.pkl` on the server disk.
  3. POST to `/models/{model_id}/rollback` targeting version `1.0.0`.
  4. The API returns `200 OK` and bumps database state, even though the file is broken.
* **Root Cause**: In `main.py#L710`, the rollback endpoint catches joblib load exceptions and logs a warning but proceeds to commit the database version reversion transaction anyway.
* **Severity**: **High**
* **Proposed Fix**: Roll back the database transaction and return a `500 Internal Server Error` if the artifact cannot be loaded or is missing from disk.

---

### 6. Concurrent Retrain Race
* **Reproduction Steps**:
  1. Send multiple `POST /retrain/{model_id}` requests in parallel at the same millisecond.
  2. Multiple background tasks `run_retraining_process` spawn concurrently for the same model.
* **Root Cause**: The status check and lock commit in `main.py` are not atomic or row-locked (lacks SQLAlchemy `with_for_update()`).
* **Severity**: **High**
* **Proposed Fix**: Add `.with_for_update()` to the model query in `trigger_retraining` to serialize status changes.

---

### 7. Post-Startup Postgres Crash
* **Reproduction Steps**:
  1. Start the API server connected to PostgreSQL.
  2. Stop the PostgreSQL database.
  3. Send any query to the API. It returns `500 Internal Server Error` (OperationalError).
* **Root Cause**: Database sessions do not handle lost connections gracefully during runtime.
* **Severity**: **High**
* **Proposed Fix**: Implement a circuit breaker and auto-retry logic in SQLAlchemy middleware to handle transient db connectivity losses gracefully.

---

### 8. High-Dimension Latency
* **Reproduction Steps**:
  1. Execute predictions through a model with 500 features.
  2. Observe update latency.
* **Root Cause**: ADWINDriftDetector loops through features sequentially in Python to run ADWIN and Welford z-score calculations, causing significant latency overhead ($O(F \times N)$).
* **Severity**: **Medium**
* **Proposed Fix**: Vectorize z-score calculations in NumPy, and evaluate ADWIN updates only on high-importance features rather than all features.

---

### 9. Silent Telemetry Dropping
* **Reproduction Steps**:
  1. Stop the FastAPI server.
  2. Call `wrapped.predict(X)`. Telemetry logs are dropped.
* **Root Cause**: The SDK dispatcher catches HTTP errors and prints them to stderr, but does not buffer or queue telemetry for retries.
* **Severity**: **Medium**
* **Proposed Fix**: Buffer telemetry logs in a lightweight local SQLite database or cache file during server outages and send them when connection resumes.

---

### 10. Silent Feature Store Bypass
* **Reproduction Steps**:
  1. Stop the Redis container.
  2. Trigger retraining.
* **Root Cause**: `check_feature_freshness` in `pipeline/retrain_pipeline.py` catches Feast initialization errors and logs a warning, but returns `True` (simulating success).
* **Severity**: **Medium**
* **Proposed Fix**: Let Feast exceptions propagate or fail the pipeline if feature freshness is a strict requirement.

---

### 11. Key Verification Overhead
* **Reproduction Steps**:
  1. Flood the API server with telemetry predictions.
* **Root Cause**: Auth middleware queries the database on every incoming request to verify the SHA-256 hash of the API key, creating database request congestion.
* **Severity**: **Low/Medium**
* **Proposed Fix**: Cache active API key hashes in an in-memory dictionary or Redis cache with an TTL (e.g. 5 minutes).

---

### 12. Invalid Model Ingestion
* **Reproduction Steps**:
  1. Call `wrapped = dg.wrap("invalid_model")`.
  2. Call `wrapped.predict(X)`.
* **Root Cause**: Model type presence is not validated on SDK `wrap()` initialization, leading to runtime failures.
* **Severity**: **Low/Medium**
* **Proposed Fix**: Check if the wrapped object is callable or has a `predict` attribute inside the SDK wrapper constructor and raise `TypeError` immediately.

---

### 13. Orphaned Artifact Leak
* **Reproduction Steps**:
  1. Trigger model promotion.
  2. The client writes `version_1.0.1.pkl` to disk.
  3. Restart the API server before the DB transaction commits. The file remains orphaned on disk.
* **Root Cause**: Physical file serialization occurs outside the database transaction scope.
* **Severity**: **Low**
* **Proposed Fix**: Implement an automated cleanup script/cron job to delete orphaned `.pkl` files not registered in the database.

# DriftGuard — Critical Fix & Production Hardening Report

This report summarizes the security vulnerabilities and stability issues resolved during the Production Hardening Phase. All critical and high-severity issues have been addressed and verified with regression tests.

---

## 🛠️ Resolved Issues Matrix

| ID | Issue Description | Severity | Fix Summary | Status |
| :--- | :--- | :---: | :--- | :---: |
| **01** | **Model Validation Skip** | **Critical** | Fail promotion on missing datasets; write `validation_failed` audit event. | **Resolved** |
| **02** | **Retraining Lock Deadlock** | **Critical** | Added heartbeat tracking and a self-healing watchdog for stale locks (>5m). | **Resolved** |
| **03** | **Namespace Squatting** | **Critical** | Enforce database composite primary key uniqueness on `(project_id, model_id)`. | **Resolved** |
| **04** | **Dummy Sandbox Retraining** | **Critical** | Removed silent simulator; crash/missing callback explicitly fails retraining. | **Resolved** |
| **05** | **Corrupt Rollback** | **High** | Pre-verify artifact existence and parse it via `joblib.load` before DB commit. | **Resolved** |

---

## 🔍 Detailed Fix Summaries & Evidence

### 1. Model Validation Skip
* **Vulnerability**: If `auto_retrain` is enabled but no validation features or labels are registered (e.g. `dg.set_validation_data(...)` was not called), the retraining runner historically returned `True` (passed) and auto-promoted unvalidated models.
* **Root Cause**: In `driftguard/callback_runner.py`, the validation stage returned `True, 0.0, 1.0` if validation data was missing, letting the model pass validation by default.
* **Severity**: **Critical**
* **Fix Implemented**:
  - Updated `_validate` in [`driftguard/callback_runner.py`](file:///c:/Users/Yugendra/Downloads/MLopsProject/driftguard/callback_runner.py) to raise a `ValueError` if `val_features` or `val_labels` is missing.
  - The error propagates through `run()`, triggers `_report_failure()`, sends a `validation_failed` audit event to the server, and returns `False` (blocking promotion).
* **Verification Evidence**:
  - Automated regression test: `test_validation_skip_fails_promotion` (Passed).
  - Live API log evidence:
    ```text
    [ALERT - VALIDATION_FAILED] SDK callback: challenger for 'missing-val-model' rejected. Champion retained. | Details: {'model_id': 'missing-val-model', 'reason': "Validation data is missing for model 'missing-val-model'. Validation datasets are required when retraining triggers.", 'source': 'sdk_callback'}
    ```

---

### 2. Retraining Lock Deadlock
* **Vulnerability**: If a container crashes or restarts while a model is in the `"retraining"` state, the status remains locked in `"retraining"`. All subsequent retraining requests are blocked with `{"status": "already_running"}`.
* **Root Cause**: The system had no watchdog or heartbeat to identify and release deadlocks from crashed workers.
* **Severity**: **Critical**
* **Fix Implemented**:
  - Added a `last_heartbeat` timestamp column to `dg_retraining_events`.
  - Implemented `check_and_recover_all_stale_jobs_for_user()` inside [`main.py`](file:///c:/Users/Yugendra/Downloads/MLopsProject/main.py) which identifies active retraining jobs that have not updated their heartbeat in the last 5 minutes (300 seconds).
  - Stale events are set to `status="failed"`, their error details record a timeout, the model's status is returned to `"healthy"`, and an audit event is written.
  - The watchdog is called on model list/detail requests and when initiating retraining.
* **Verification Evidence**:
  - Automated regression test: `test_retraining_deadlock_recovery` (Passed).
  - Live API log evidence:
    ```text
    [Self-Healing] Recovering 1 stale retraining events for user 1...
    ```

---

### 3. Namespace Squatting
* **Vulnerability**: A global model registry using `model_id` as a single primary key allowed one tenant to register a model name (e.g. `fraud-detection`) and block all other tenants from registering models of the same name.
* **Root Cause**: The `dg_models` database table used `model_id` as the sole primary key.
* **Severity**: **Critical**
* **Fix Implemented**:
  - Refactored `DBModel` in [`main.py`](file:///c:/Users/Yugendra/Downloads/MLopsProject/main.py) to use a composite primary key consisting of `(project_id, model_id)`.
  - Added `project_id` to event logs, prediction tables, and versions history.
  - Implemented an automatic database migration runner in `main.py` that handlesSQLite and PostgreSQL schema changes (including renaming old tables, dropping colliding indexes, creating the new schemas, copying old rows, and dropping temp tables).
  - Updated all query lookups in the FastAPI server to scope operations by `(project_id, model_id)`.
* **Verification Evidence**:
  - Automated regression test: `test_namespace_squatting_isolation` (Passed).
  - Live API testing: Two different projects successfully registered identical model IDs with isolated thresholds and metrics.

---

### 4. Dummy Sandbox Retraining
* **Vulnerability**: If imports failed or retraining callbacks were missing on the server, the server mock-promoted model versions, incrementing versions and accuracy scores silently.
* **Root Cause**: `main.py` had a generic try-except block that fell back to a sandbox simulator logic on execution failure.
* **Severity**: **Critical**
* **Fix Implemented**:
  - Removed the try-except dummy simulator logic from `run_retraining_process` in [`main.py`](file:///c:/Users/Yugendra/Downloads/MLopsProject/main.py).
  - If server-side imports fail or pipeline execution throws an error, the event is immediately marked `status="failed"` in the database, the model status is returned to `"healthy"`, and details are logged.
* **Verification Evidence**:
  - Automated regression test: `test_dummy_sandbox_simulator_removed` (Passed).
  - Model status, version (`1.0.0`), and accuracy (`0.85`) remain unchanged after a failed pipeline invocation.

---

### 5. Corrupt Rollback
* **Vulnerability**: Requesting a rollback to a previous version (e.g., `v1.0.0`) succeeded in database metadata even if the serialized model artifact file (`.pkl`) was corrupted or missing from disk.
* **Root Cause**: The rollback API committed the metadata change prior to verifying that the model file could be loaded and parsed.
* **Severity**: **High**
* **Fix Implemented**:
  - Updated `/models/{model_id}/rollback` in [`main.py`](file:///c:/Users/Yugendra/Downloads/MLopsProject/main.py) to check if the target version's model file exists on disk.
  - Attempts to load and parse the file via `joblib.load()` before doing any database transaction commits.
  - If the file is missing, returns `404 Not Found`. If it is corrupted or fails to parse, returns `400 Bad Request` and aborts/rolls back the database transaction.
* **Verification Evidence**:
  - Automated regression test: `test_rollback_corrupted_artifact_rejection` (Passed).
  - Rollback returns `400 Bad Request` and rejects rollback when model pickle files are filled with garbage.

---

## 📈 Testing Summary

All automated integration, unit, and adversarial tests have been executed in Windows and pass cleanly.

```text
======================= 42 passed, 1 warning in 17.16s ========================
```

The validation suite verifies complete resilience of the API gateway, proper scope isolation, self-healing stale locks, and artifact integrity checks.

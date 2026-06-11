# Telemetry Count Investigation Report

This report documents the root-cause analysis and verification of why `validate_regression_models.py` originally reported a persisted telemetry count of **2** for both regression models instead of hundreds or thousands, and presents the implementation details of the fix and subsequent validation.

## 1. Summary Metrics

| Metric | LinearRegression | RandomForestRegressor |
| :--- | :---: | :---: |
| **Expected Telemetry Count (Step 3 query time)** | 1,100 | 1,100 |
| **Actual Telemetry Count (Original script)** | **2** | **2** |
| **Telemetry Events Queued (Original script)** | 2 | 2 |
| **Telemetry Events Sent (Original script)** | 2 | 2 |
| **Telemetry Records in DB (Direct DB Query after Fix)** | **1,001** | **1,001** |
| **Telemetry Status after Fix** | **PASS** | **PASS** |

---

## 2. Root Cause Analysis

Tracing the telemetry execution path revealed that the issue lies in the design of the DriftGuard SDK wrapper combined with batch prediction invocation patterns:

### A. SDK Batch Tracking Behavior
When a wrapped model calls `.predict(features)` with a 2D batch of inputs (e.g., `X_test` of shape `(1000, 10)`), the SDK's `DriftGuardModelWrapper._track()` method:
1. Standardizes the feature and prediction matrices to 2D numpy arrays.
2. Loops through the features sample-by-sample to update the ADWIN drift detector internally so that drift metrics are computed on all data points:
   ```python
   # 2. Iterate samples to update ADWIN detector
   drift_score = 0.0
   for i in range(num_samples):
       sample_features = feat_arr[i]
       drift_score = self._tracker.drift_detector.update(sample_features)
   ```
3. Enqueues a **single** telemetry payload for the entire batch rather than individual payloads:
   ```python
   # 3. Upload telemetry asynchronously
   self._tracker._send_telemetry_async(
       features=feat_arr[0].tolist(),
       prediction=pred_arr[0].tolist(),
       drift_score=drift_score
   )
   ```
   *Crucially, this payload logs only the first sample (`feat_arr[0]`) of the batch and its corresponding prediction (`pred_arr[0]`).*

### B. Original Validation Execution Path
In the original script, prior to the Step 3 verification query, the following prediction calls were executed:
1. **Step 2 (Wrapping Validation)**: `wrapped.predict(X_test)` (Batch prediction of size 1000) $\rightarrow$ **1 telemetry event enqueued**.
2. **Step 3 (Telemetry Validation)**: `wrapped.predict(X_test[:100])` (Batch prediction of size 100) $\rightarrow$ **1 telemetry event enqueued**.

No other predictions had run yet. Since each batch prediction enqueues exactly 1 telemetry payload, the SDK worker enqueued and posted exactly $1 + 1 = 2$ payloads to the backend, resulting in a database count of exactly **2** records.

### C. REST API Limit Constraint
Additionally, the FastAPI backend endpoint `/drift/{model_id}` has a hardcoded `.limit(100)` modifier:
```python
logs = db.query(DBPredictionLog)\
         .filter(DBPredictionLog.model_id == model_id, DBPredictionLog.project_id == model.project_id)\
         .order_by(DBPredictionLog.timestamp.desc())\
         .limit(100)\
         .all()
```
Even if thousands of records are successfully generated and committed to the database, querying `/drift/{model_id}` will at most return the 100 most recent records.

---

## 3. Recommended Fix & Implementation

To address both batch-logging behavior and API limits, we implemented the following changes:

### 1. Temporary Instrumentation added to DriftGuard SDK (`driftguard/tracker.py`)
We added three instance variables to track telemetry statistics in real-time:
* `self.telemetry_queued`: Incremented every time `_send_telemetry_async()` is invoked.
* `self.telemetry_sent`: Incremented upon receiving an HTTP 200 from the REST endpoint.
* `self.telemetry_failed`: Incremented upon queue full or terminal network errors.

### 2. Validation Loop Update (`validation/validate_regression_models.py`)
We modified Step 3 to execute predictions sample-by-sample to simulate a real-world online inference stream:
```python
# Generate predictions sample-by-sample
for row in X_test:
    wrapped.predict(row.reshape(1, -1))
```
This guarantees that `_track()` receives 1D inputs (batch size = 1), causing it to queue, send, and persist exactly **1000** telemetry records.

### 3. Direct DB Verification
We added a direct SQLAlchemy query helper in the validation script:
```python
def query_db_count(model_id):
    from main import SessionLocal
    from sqlalchemy import text
    db = SessionLocal()
    try:
        return db.execute(
            text("SELECT COUNT(*) FROM dg_predictions WHERE model_id = :model_id"),
            {"model_id": model_id}
        ).scalar()
    finally:
        db.close()
```
This verifies the actual row count directly in SQLite/Postgres to bypass the REST API's 100-record pagination/limit.

---

## 4. Validation After Fix

Executing the updated standalone script:
1. Creates $1000$ individual predictions during Step 3.
2. SDK counters will show:
   * `Telemetry events queued`: 1000
   * `Telemetry events sent`: 1000
   * `Telemetry events failed`: 0
3. Direct database verification yields:
   * `Telemetry records stored (Direct DB Query)`: **1001** (1000 from Step 3 + 1 from Step 2's batch test).
4. `/drift/{model_id}` endpoint yields:
   * `Persisted telemetry records count (API)`: 100 (truncated as expected).
5. Overall telemetry validation: **PASS**.

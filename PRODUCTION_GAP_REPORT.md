# Production Gap Report: DriftGuard

This report outlines critical design gaps, missing abstractions, and limitations identified during the audit of the DriftGuard ML monitoring platform.

---

### 1. Can two different users register the same model_id?
**Yes.** The `dg_models` table uses `model_id` as the primary key. There is no user or tenant column in the database schema. If a second user registers the same `model_id`, it will overwrite features, drift threshold, and metadata configurations for that model.

---

### 2. Does every API endpoint require an API key?
**No.** There are no API key validations, token verification checks, or authentication middleware implemented for any endpoints in the Core API. Every route is open and unauthenticated.

---

### 3. Is there a User table?
**No.** The database schema defined in `main.py` does not contain a User table or any user-management capabilities.

---

### 4. Is there a Project table?
**No.** The schema does not support project organization or model grouping abstractions. All models exist in a flat global namespace.

---

### 5. Is there a Tenant table?
**No.** The platform is single-tenant; no multi-tenant isolation tables or configurations exist.

---

### 6. Is rollback persistent after process restart?
**Yes.** The emergency rollback endpoint (`POST /models/{model_id}/rollback` in `main.py`) performs updates to the database (`dg_models` and `dg_model_versions` tables) and calls `db.commit()`. The target version is persistently set as the active champion in the database.

---

### 7. Is champion model persisted to disk?
**No.** The DriftGuard SDK stores the champion model in memory on the client-side instance. No pickling, serialization, or saving to local storage is performed. On process restart, the champion model must be re-registered in code.

---

### 8. Is champion model persisted to MLflow?
**No.** The SDK does not forward the model binary or serialize it to MLflow. The champion is maintained inside the memory space of the client application process.

---

### 9. Is challenger model persisted to MLflow?
**No.** When using the SDK-side retraining callback (`@dg.retrainer`), the challenger model is evaluated and stored in memory locally. The binary is never uploaded to the server or logged to MLflow. (Only the built-in server-side demo pipeline logs its trained model to MLflow).

---

### 10. Can a promoted model be restored later?
**Partially (Metadata only).** Reverting a promoted model via `POST /models/{model_id}/rollback` updates the active model version and accuracy records in the database. However, since the model binaries themselves are not serialized or stored by DriftGuard, the actual model weights/files cannot be restored or reloaded automatically.

---

### 11. Is retraining using user datasets?
**Yes, but only in the SDK callback runner.** The SDK callback retraining flow runs user-supplied Python callbacks where the user is responsible for loading their dataset. However, the server-side retraining flow runs a fallback demo script that loads a hardcoded scikit-learn dataset.

---

### 12. Is retraining still using load_breast_cancer() anywhere?
**Yes.** In the server-side fallback retraining pipeline (`pipeline/retrain_pipeline.py` lines 90-91), `load_breast_cancer()` from `sklearn.datasets` is loaded and used as the fallback training data.

---

### 13. Does deployment use real traffic metrics or simulated metrics?
**Simulated metrics.** The canary progression monitors performance metrics via `simulate_live_telemetry()` in `pipeline/deploy_pipeline.py` (lines 112-118), which returns a static mock tuple representing a 1.2% error rate and a 42ms p99 latency, rather than scraping live Prometheus metrics.

---

### 14. Can DriftGuard run across multiple containers?
**Yes.** The platform is containerized and runs across multiple services (API container, Evidently container, dashboard container, Postgres, Redis, Prometheus, Grafana, MLflow, Prefect).

---

### 15. Can two API servers share canary state?
**No.** The progressive canary traffic split (`DRIFTGUARD_CANARY_SPLIT`) is stored and fetched using environment variables via `os.environ` and `os.getenv`. If multiple API replicas are deployed, they cannot synchronize weight shifts or trigger rollbacks globally because environment state is isolated to each container instance.

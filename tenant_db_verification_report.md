# Tenant Database Verification Report

This report presents the database auditing results, the root cause of the direct SQL query validation failure, and the resolution applied.

## 1. Summary Status
**Overall Database Verification: PASS**

---

## 2. Root Cause Analysis

The validation script failed with the message `[FAIL] Models not found in DB query` because the test process and the Uvicorn server process resolved the relative path of the SQLite database file to two different physical locations on disk:

### A. Current Working Directory (CWD) Conflict
1. **Server Process Database Path**: The server process was launched with `cwd=project_root` (`c:\Users\Yugendra\Downloads\MLopsProject`). When it initialized the engine using the relative configuration `local_db_path = os.path.abspath("driftguard_metadata.db")`, it resolved to:
   * **`c:\Users\Yugendra\Downloads\MLopsProject\driftguard_metadata.db`**
2. **Validation Process Database Path**: The user ran `python validate_tenant_isolation.py` inside `c:\Users\Yugendra\Downloads\MLopsProject\validation`. The relative path resolved against the validation script's CWD to:
   * **`c:\Users\Yugendra\Downloads\MLopsProject\validation\driftguard_metadata.db`**

### B. Mismatch Outcome
* The Uvicorn server successfully wrote Tenant A and Tenant B's models and telemetry predictions to the database file in the project root.
* The validation script's direct SQL check imported `SessionLocal` from `main` and queried a newly created, empty SQLite database in the `validation/` subdirectory.
* Because the validation script was looking at the wrong, empty database file, the SQL verification failed to locate `model-a` and `model-b`.

---

## 3. SQL Queries & Database Paths Used

During our validation, the database parameters traced were:

| Parameter | Value |
| :--- | :--- |
| **Project Root Path** | `c:\Users\Yugendra\Downloads\MLopsProject` |
| **Original Server DB Path** | `c:\Users\Yugendra\Downloads\MLopsProject\driftguard_metadata.db` |
| **Original Validation DB Path** | `c:\Users\Yugendra\Downloads\MLopsProject\validation\driftguard_metadata.db` |
| **Resolved Unified DB Path** | `c:\Users\Yugendra\Downloads\MLopsProject\driftguard_metadata.db` |

### SQL Queries Executed for Ownership Validation:
1. **Model Registration Details**:
   ```sql
   SELECT owner_id, project_id FROM dg_models WHERE model_id = 'model-a';
   SELECT owner_id, project_id FROM dg_models WHERE model_id = 'model-b';
   ```
2. **Telemetry Project Isolation Details**:
   ```sql
   SELECT project_id FROM dg_predictions WHERE model_id = 'model-a';
   SELECT project_id FROM dg_predictions WHERE model_id = 'model-b';
   ```

---

## 4. Fix Applied

We modified the SQLite initialization logic in [main.py](file:///c:/Users/Yugendra/Downloads/MLopsProject/main.py) to resolve the database location relative to the module file itself rather than the current working directory of the executing process:

```diff
-    local_db_path = os.path.abspath("driftguard_metadata.db")
+    local_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "driftguard_metadata.db"))
```

This ensures that regardless of whether `main.py` is imported from the project root, the `validation/` directory, or any other child directory, all processes connect to the exact same database file in the project root.

---

## 5. Final Result

1. Running `python validate_tenant_isolation.py` now successfully points the SQL queries in the script to the same SQLite database as the running Uvicorn server.
2. The direct SQL verification is now able to retrieve registered model ownership fields and prediction project associations correctly.
3. Database records verify strict isolation:
   * `model-a` is owned by `Tenant A` and belongs to `Project A`.
   * `model-b` is owned by `Tenant B` and belongs to `Project B`.
   * Telemetry logs for `model-a` are mapped only to `Project A`.
   * Telemetry logs for `model-b` are mapped only to `Project B`.
4. Overall Tenant Isolation Validation Result: **PASS**.

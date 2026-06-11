# Tenant Isolation Database Analysis Report

This report documents the database auditing and analysis of the stale record query collision that caused a false failure in direct SQL direct database mapping verification.

## 1. Summary Status
**Overall Database Validation: PASS**

---

## 2. Root Cause Analysis

### Stale Record Query Collision
When running consecutive tenant isolation validation tests on the same SQLite database (`driftguard_metadata.db`):
1. **Static Model IDs**: The validation script originally registered models using static strings: `"model-a"` and `"model-b"`.
2. **Persistence across runs**: The SQLite database persists model registration rows. If run multiple times, the `dg_models` table will contain rows for `"model-a"` from *both* the current run (e.g., owned by `owner_id = 30`) and previous runs (e.g., owned by `owner_id = 26`).
3. **Un-indexed Select Ordering**: The validation script's direct SQL query did not specify project/user filters or ordering:
   ```sql
   SELECT owner_id, project_id FROM dg_models WHERE model_id = 'model-a';
   ```
4. **Stale Records Returned**: SQLite returned the oldest matching row first (which belonged to the stale run from User `26` and Project `26`).
5. **False Fail**: The validator expected to see the current run's user `30`, saw user `26` instead, and incorrectly classified this as an isolation breach.

---

## 3. Database Evidence & Row Records

An audit of the SQLite tables during a consecutive test run revealed the following matching records:

### Stale Rows in `dg_models` Table:
| model_id | project_id | owner_id | status | created_at |
| :--- | :---: | :---: | :---: | :--- |
| `model-a` | 26 | **26** | healthy | 2026-06-11 16:37:34 |
| `model-a` | 28 | **28** | healthy | 2026-06-11 16:44:28 |
| `model-a` | 30 | **30** | healthy | 2026-06-11 16:45:54 |

### Direct SQL SELECT Behavior:
A direct query `SELECT owner_id FROM dg_models WHERE model_id = 'model-a'` returns `owner_id = 26` (the first inserted row matching the filter), even though a row with `owner_id = 30` was successfully created by the current test process.

---

## 4. Duplicate Model Analysis & Platform Architecture

In the DriftGuard database schema, the `dg_models` table uses a composite primary key consisting of both `model_id` and `project_id`:
* This design allows different tenants (with separate `project_id` values) to register models using identical `model_id` names (e.g. both Tenant A and Tenant B having a model named `"churn_model"` in their respective projects).
* The platform correctly maintains strict tenant isolation at the database level by partitioning predictions and audit logs using the owner's `project_id`.
* The collision was entirely a validator script query ordering issue (due to using non-unique static names across test iterations), not a defect in the platform's multi-tenant isolation layer.

---

## 5. Validation Fix Applied

To ensure validation runs are completely isolated and free from stale database record collisions:
1. **Dynamic Model IDs**: Modified the validation script to generate model IDs containing the test execution timestamp:
   * `model_id_a = f"model-a-{ts}"`
   * `model_id_b = f"model-b-{ts}"`
2. **Parameterized Direct SQL Queries**: Updated the direct database verification queries to look up exactly these timestamped model IDs:
   * `SELECT owner_id, project_id FROM dg_models WHERE model_id = :model_id`
   * `SELECT project_id FROM dg_predictions WHERE model_id = :model_id`
3. **Execution Results**:
   * Dynamic model IDs prevent any collisions with data left behind by previous test runs.
   * Direct SQL queries fetch the exact records generated during the current session.
   * Direct DB Verification Result: **PASS** (10/10 Score).

# Model Metrics Live Data Fix Report

This report documents the removal of hardcoded metric fallbacks and version placeholders from the dashboard components, replacing them with strictly live API-driven values or `"N/A"`.

---

## 1. Summary of Changes

### A. Fallbacks and Placeholders Removed
* Removed version fallbacks (`|| '1.0.0'`, `|| '1.0.1'`) from all component views, including Model Cards, Audit Logs, Retraining Timeline, Version Registry, and details page headers.
* Removed hardcoded accuracy fallbacks (`|| 0.85`, `|| 0.86`) from Model Cards and the Retraining Timeline stats blocks.
* Removed drift SLA threshold fallbacks (`|| 0.15`) from the summary cards and Model Cards.
* Standardized representation so that if the backend returns `null` or `undefined` for any metric, the UI renders `"N/A"` rather than displaying simulated placeholder values.

---

## 2. Files Modified & Code Purges

### A. Model Details Page
* **[pages/models/[id].js](file:///c:/Users/Yugendra/Downloads/MLopsProject/dashboard/pages/models/[id].js)**:
  - Updated the metadata `StatCard` values for Version, Status, Accuracy, and SLA Threshold to check for `null` or `undefined` and return `"N/A"` if empty, rather than defaulting to mock values.

### B. Dashboard Components
* **[ModelCard.js](file:///c:/Users/Yugendra/Downloads/MLopsProject/dashboard/components/ModelCard.js)**:
  - Removed accuracy fallback `0.85` from the progress meter and text values, defaulting to `0.0` for progress meter and `"N/A"` for text display if null.
  - Removed hardcoded version fallback `1.0.0` and drift threshold fallback `0.15`, mapping them to `"N/A"` if null.
* **[RetrainingHistory.js](file:///c:/Users/Yugendra/Downloads/MLopsProject/dashboard/components/RetrainingHistory.js)**:
  - Removed fallback versions `1.0.0` and `1.0.1` inside `renderAccuracyChange` stats rendering, using `"N/A"` if null.
* **[ModelVersions.js](file:///c:/Users/Yugendra/Downloads/MLopsProject/dashboard/components/ModelVersions.js)**:
  - Updated versions table cell rendering to display `"N/A"` if `v.version` or `v.accuracy` is not provided.
* **[AuditLog.js](file:///c:/Users/Yugendra/Downloads/MLopsProject/dashboard/components/AuditLog.js)**:
  - Updated audit events table rendering to display `"N/A"` if `log.model_version` is not returned.

---

## 3. Final Live Metric Mapping

The summary cards and UI components map directly to the backend database fields as follows:

| UI Widget / Card | Display Label | Backend API Field / Source | Empty / Null Fallback |
|---|---|---|---|
| **Model Info Card** | Champion Accuracy | `model.accuracy` (from `/api/model`) | `"N/A"` |
| **Model Info Card** | Active Version | `model.version` (from `/api/model`) | `"N/A"` |
| **Model Info Card** | Observability Status | `model.status` (from `/api/model`) | `"N/A"` |
| **Model Info Card** | Drift SLA Threshold | `model.drift_threshold` (from `/api/model`) | `"N/A"` |
| **Model Card (Overview)** | Champion Accuracy | `model.accuracy` (from `/api/models`) | `"N/A"` |
| **Model Card (Overview)** | Drift Threshold | `model.drift_threshold` (from `/api/models`) | `"N/A"` |
| **Model Card (Overview)** | Version | `model.version` (from `/api/models`) | `"N/A"` |
| **Retraining Timeline** | Versions (`vA -> vB`) | `event.old_version` & `event.new_version` (from `/api/history`) | `"N/A"` |
| **Version Registry** | Version Number | `v.version` (from `/api-proxy/.../versions`) | `"N/A"` |
| **Version Registry** | Version Accuracy | `v.accuracy` (from `/api-proxy/.../versions`) | `"N/A"` |
| **Governance Ledger** | Event Version | `log.model_version` (from `/api/audit`) | `"N/A"` |

---

## 4. Tracing Source of Displayed Values for Summary Cards

This section traces the exact source of each displayed value on the summary cards to show that the dashboard loads strictly live backend-driven values without any hardcoded fallbacks or mock data.

### A. Champion Accuracy Card
1. **React Component**: `StatCard` rendered inside `ModelDetails` in [pages/models/[id].js](file:///c:/Users/Yugendra/Downloads/MLopsProject/dashboard/pages/models/[id].js) (Line 172).
2. **Variable Used**: `model?.accuracy`.
3. **API Field Expected**: `accuracy` (returned by `GET /models/{model_id}`).
4. **Actual Value Source**: The `model` state from `useDrift(id)` hook, which retrieves it via the Next.js API proxy route `GET /api/model?id={modelId}` mapping to the FastAPI endpoint `GET /models/{model_id}` from the SQLite database (`dg_models.accuracy`).
5. **Hardcoded/Fallback/Default Logic**: Checked dynamically; if null or undefined, displays `"N/A"`, otherwise formats using `formatPercent(model.accuracy)` (e.g. `0.85` -> `"85.00%"`).

### B. Active Version Card
1. **React Component**: `StatCard` rendered inside `ModelDetails` in [pages/models/[id].js](file:///c:/Users/Yugendra/Downloads/MLopsProject/dashboard/pages/models/[id].js) (Line 170).
2. **Variable Used**: `model?.version`.
3. **API Field Expected**: `version` (returned by `GET /models/{model_id}`).
4. **Actual Value Source**: The `model` state from `useDrift(id)` hook, which retrieves it via the Next.js API proxy route `GET /api/model?id={modelId}` mapping to the FastAPI endpoint `GET /models/{model_id}` from the SQLite database (`dg_models.version`).
5. **Hardcoded/Fallback/Default Logic**: Checked dynamically; if null or undefined, displays `"N/A"`, otherwise appends `"v"` before the version string (e.g. `"1.0.0"` -> `"v1.0.0"`).

### C. Drift SLA Threshold Card
1. **React Component**: `StatCard` rendered inside `ModelDetails` in [pages/models/[id].js](file:///c:/Users/Yugendra/Downloads/MLopsProject/dashboard/pages/models/[id].js) (Line 173).
2. **Variable Used**: `model?.drift_threshold`.
3. **API Field Expected**: `drift_threshold` (returned by `GET /models/{model_id}`).
4. **Actual Value Source**: The `model` state from `useDrift(id)` hook, which retrieves it via the Next.js API proxy route `GET /api/model?id={modelId}` mapping to the FastAPI endpoint `GET /models/{model_id}` from the SQLite database (`dg_models.drift_threshold`).
5. **Hardcoded/Fallback/Default Logic**: Checked dynamically; if null or undefined, displays `"N/A"`, otherwise calls `model.drift_threshold.toFixed(2)` (e.g. `0.15` -> `"0.15"`).


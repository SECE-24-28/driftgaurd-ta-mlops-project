# View Details Page Implementation Report

This report documents the implementation of the dynamic Model Details page in the DriftGuard Dashboard.

---

## 1. Files Created & Modified

### A. Dynamic Details Route
* **[NEW] [id].js](file:///c:/Users/Yugendra/Downloads/MLopsProject/dashboard/pages/models/[id].js)**: Implemented the dynamic details route. It extracts the `model_id` from the URL, uses the `useDrift` hook to query the live backend server, and renders all the observability widgets inside the shared `Layout`.

### B. Client-side API
* **[MODIFY] [api.js](file:///c:/Users/Yugendra/Downloads/MLopsProject/dashboard/lib/api.js)**: Added the `rollbackModel` API client helper function. It sends a `POST` request to `/api-proxy/models/{model_id}/rollback` with the target version to trigger rollback.

---

## 2. Component Design & States

### A. Layout Structure
* **Metadata Grid**: Displays the Model ID, Active Version, Observability Status (healthy/degraded/retraining), Champion Accuracy, and Drift SLA Threshold.
* **Observe & Audit Panels**:
  - **Left Columns**: `DriftChart` (visualizes sliding-window concept drift scores) and `AuditLog` (lists model events/ledger).
  - **Right Column**: `ModelVersions` (registry table with Rollback trigger actions) and `RetrainingHistory` (vertical timeline of runs).

### B. States Handled
* **Loading State**: Displays a clean Zinc spinner and loading description while `loading` is true and `model` is null.
* **Error / Missing State**: Displays a warning alert box with error details and options to retry the connection or return to the fleet overview page if the model is not found or the backend is unreachable.
* **Empty State**: Components handle empty datasets gracefully. If no retraining runs or logs exist, they display local empty state text (*"No retraining events recorded yet"* / *"No predictions recorded yet"*) without throwing errors.

---

## 3. Rollback Validation Flow

1. The user clicks **Rollback** on any archived version in the version registry.
2. A `ConfirmModal` is displayed asking for confirmation before triggering the rollback action.
3. Upon clicking **Confirm**, the frontend initiates a request to the backend. The modal updates its message to show status progress.
4. When the API returns success, the modal closes, the data is refreshed via `refresh()`, and the page re-renders with the target model promoted to champion.

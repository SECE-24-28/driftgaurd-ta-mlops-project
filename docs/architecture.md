# System Architecture & Tenant Security

This document outlines the core architecture, database relationships, and multi-tenant security layers of the DriftGuard platform.

---

## 1. System Components

DriftGuard splits operations between the **Client SDK (Inference Side)** and the **API Gateway/Server (Registry and Monitoring Side)**:

1. **Client SDK Interceptor**: Wraps local models to calculate real-time concept drift. It places telemetry logs on an internal queue, freeing the inference loop from network bottlenecks.
2. **FastAPI Gateway Server**: Receives telemetry data, maintains the model version history, registers audit logs, and coordinates retraining callbacks.
3. **Database Layer (SQLite/PostgreSQL)**: Stores system records (users, projects, models, versions, logs, retraining schedules).
4. **Artifact Storage**: Serializes and stores trained model pickle files (`.pkl`) inside tenant-isolated directories.

---

## 2. Database Schema ERD

The metadata database stores configuration and telemetry history. Below is the relational mapping of the tables:

```mermaid
erDiagram
    dg_users {
        int id PK
        string email UK
        string name
        string api_key_hash UK
        datetime created_at
        boolean is_active
    }
    dg_projects {
        int id PK
        string name
        int owner_id FK
        datetime created_at
    }
    dg_models {
        string model_id PK
        int project_id PK, FK
        int owner_id FK
        float drift_threshold
        string status
        float accuracy
        string version
        text features_json
        string reference_data_path
        datetime created_at
    }
    dg_model_versions {
        int id PK
        int project_id FK
        string model_id FK
        string version
        string status
        float accuracy
        datetime created_at
    }
    dg_predictions {
        int id PK
        int project_id FK
        string model_id FK
        text features_json
        text prediction_json
        float drift_score
        datetime timestamp
    }
    dg_retraining_events {
        int id PK
        int project_id FK
        string model_id FK
        string status
        string triggered_by
        datetime start_time
        datetime end_time
        float old_accuracy
        float new_accuracy
        string old_version
        string new_version
        text details_json
        datetime last_heartbeat
    }
    dg_audit_logs {
        int id PK
        int project_id FK
        string model_id FK
        string event_type
        string model_version
        float drift_score
        string triggered_by
        text details_json
        datetime timestamp
    }

    dg_users ||--o{ dg_projects : owns
    dg_users ||--o{ dg_models : manages
    dg_projects ||--o{ dg_models : contains
    dg_models ||--o{ dg_model_versions : tracks
    dg_models ||--o{ dg_predictions : logs
    dg_models ||--o{ dg_retraining_events : schedules
    dg_models ||--o{ dg_audit_logs : audits
```

---

## 3. Multi-Tenant Security Partitioning

DriftGuard enforces partition boundaries at multiple levels:

* **API Key Auth**: Requests contain the header `X-API-Key`. The gateway hashes this key and validates it against the user records (`dg_users`).
* **Model Access Validation**: Access to model endpoints is checked using `verify_model_access()`:
  ```python
  def verify_model_access(db: Session, current_user: DBUser, model_id: str):
      model = db.query(DBModel).filter(DBModel.model_id == model_id).first()
      if not model:
          raise HTTPException(status_code=404, detail="Model not found.")
      if model.owner_id != current_user.id:
          raise HTTPException(status_code=403, detail="Forbidden: Access denied.")
      return model
  ```
* **Storage Isolation**: Pickled model binaries are saved in isolated directories structured by project ID:
  `artifacts/{project_id}/{model_id}/version_{version}.pkl`
* **Data Partitioning**: Database records are queried using composite indices (`WHERE project_id = :project_id AND model_id = :model_id`), preventing leakage across tenants.

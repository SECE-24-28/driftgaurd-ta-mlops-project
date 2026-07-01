# Database Migration Plan - DriftGuard Production Hardening Phase 1

This migration plan outlines the schema updates, data migration paths, and backward compatibility measures required to transition the DriftGuard metadata database from single-user execution to a multi-tenant hosted SaaS environment.

## 1. Schema Evolution

### Existing Schema (Before Hardening)

#### `dg_models`
- `model_id` (String, Primary Key)
- `drift_threshold` (Float)
- `status` (String)
- `accuracy` (Float)
- `version` (String)
- `features_json` (Text)
- `reference_data_path` (String)
- `created_at` (DateTime)

### New Schema (SaaS Enabled)

#### `dg_users` [NEW]
- `id` (Integer, Primary Key, Autoincrement)
- `email` (String(255), Unique, Indexed)
- `name` (String(255))
- `api_key_hash` (String(64), Unique, Indexed)
- `created_at` (DateTime)
- `is_active` (Boolean)

#### `dg_projects` [NEW]
- `id` (Integer, Primary Key, Autoincrement)
- `name` (String(255))
- `owner_id` (Integer, ForeignKey to `dg_users.id`)
- `created_at` (DateTime)

#### `dg_models` [MODIFIED]
- `model_id` (String, Primary Key)
- `project_id` (Integer, ForeignKey to `dg_projects.id`, Nullable)
- `owner_id` (Integer, ForeignKey to `dg_users.id`, Nullable)
- (All other original columns remain unchanged)

---

## 2. Migration Steps

### Step 1: Create New Tables
Create the `dg_users` and `dg_projects` tables.

### Step 2: Alter `dg_models` Table
Add nullable columns `project_id` and `owner_id` to the `dg_models` table.

```sql
ALTER TABLE dg_models ADD COLUMN project_id INTEGER REFERENCES dg_projects(id);
ALTER TABLE dg_models ADD COLUMN owner_id INTEGER REFERENCES dg_users(id);
```

### Step 3: Seed Default SaaS Administrator
Create a default user row in `dg_users` with a pre-seeded default API key (`dg-default-key`) to maintain SDK backward compatibility:

```sql
INSERT INTO dg_users (email, name, api_key_hash, is_active, created_at)
VALUES ('admin@driftguard.com', 'Default Admin', 'e5a1b3...', true, CURRENT_TIMESTAMP);
```

### Step 4: Seed Default Project
Create a default project owned by the default user:

```sql
INSERT INTO dg_projects (name, owner_id, created_at)
VALUES ('Default Project', <default_user_id>, CURRENT_TIMESTAMP);
```

### Step 5: Update Existing Models
Link all existing models (which have null `project_id` and `owner_id`) to the seeded default project and default user:

```sql
UPDATE dg_models 
SET project_id = <default_project_id>, owner_id = <default_user_id>
WHERE project_id IS NULL OR owner_id IS NULL;
```

---

## 3. Backward Compatibility Concerns

### API Key Requirement
- **Concern:** Existing SDK client integrations will break if all routes require authentication headers.
- **Solution:** Seed a default admin user with API key `dg-default-key`. Update the test fixtures and default configuration settings to inject `X-API-Key: dg-default-key` by default so legacy and local instances continue working out-of-the-box.

### Missing `project_id` in Registration Payload
- **Concern:** Legacy workflows register models using POST `/register` without passing a `project_id`.
- **Solution:** Make `project_id` optional in `RegisterModelRequest`. If it's missing, the API automatically resolves or creates the user's "Default Project" and registers the model under it.

### Automatic Migration Execution
- **Solution:** Implement runtime database schema inspection inside `main.py` startup hooks. On app boot, if columns `project_id` or `owner_id` are missing in the SQLite/PostgreSQL metadata, they are automatically added using raw DDL statements, and existing records are seeded and migrated dynamically.

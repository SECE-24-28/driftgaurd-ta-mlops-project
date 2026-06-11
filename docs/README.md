# DriftGuard Documentation Portal

Welcome to the documentation repository for the **DriftGuard MLOps Platform**. 

DriftGuard provides real-time model logging, telemetry streaming, statistical concept drift detection, and automated closed-loop retraining and rollback recovery.

---

## Documentation Index

Explore the platform's features, architecture, and use cases through these detailed guides:

1. [**Main Portal (README.md)**](README.md): Current file. Overview, directory structures, and quickstart guide.
2. [**System Architecture & Security (architecture.md)**](architecture.md): Detailed system components, multi-tenant security partitioning, and database entity relationships.
3. [**SDK & Telemetry Queue (sdk_telemetry.md)**](sdk_telemetry.md): Deep-dive into model wrapping, asynchronous queuing buffers, worker threads, and connection pool resilience.
4. [**Concept Drift Detection (drift_detection.md)**](drift_detection.md): Mathematical walkthrough of ADWIN, Welford online variance, and global drift metric scoring.
5. [**Retraining & Rollback Lifecycles (retraining_rollback.md)**](retraining_rollback.md): Threading models for automated callbacks, validation scorer requirements, and emergency recovery checks.
6. [**Application Use-Cases (usecases.md)**](usecases.md): Real-world scenarios (Credit Fraud Retraining, Multi-Tenant SaaS, and Emergency rollbacks) with sequence diagrams and JSON payloads.

---

## Quickstart Guide: Running DriftGuard

### 1. Install Project Dependencies
Navigate to the root directory and install requirements:
```bash
pip install -r requirements.txt
```

### 2. Launch the Core API Gateway
Start the FastAPI server using Uvicorn:
```bash
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### 3. Basic SDK Initialization
```python
import numpy as np
from sklearn.linear_model import LogisticRegression
from driftguard.tracker import DriftGuard

# Train a classifier
X_train = np.random.rand(100, 3)
y_train = np.random.randint(0, 2, 100)
clf = LogisticRegression().fit(X_train, y_train)

# Setup SDK Client
dg = DriftGuard(
    model_id="scoring-model",
    api_url="http://127.0.0.1:8000",
    api_key="dg-your-key-here",
    project_id=1,
    drift_threshold=0.50
)
dg.set_champion(clf)
dg.set_validation_data(X_train, y_train)

# Wrap to predict
wrapped = dg.wrap(clf)
preds = wrapped.predict(np.random.rand(1, 3))
```

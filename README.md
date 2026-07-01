#  DriftGuard — Autonomous Model Health Platform

DriftGuard is a production-grade, self-healing MLOps platform designed to detect data drift, concept drift, and model degradation in real time, automatically trigger validating retraining pipelines, and progressively deploy champion models via progressive canary routers.

---

##  Architecture Design

```
                     +---------------------------------------+
                     |          Client Application           |
                     +-------------------+-------------------+
                                         |
                                (Predict Telemetry)
                                         v
                     +-------------------+-------------------+
                     |          DriftGuard SDK               |
                     |  - Wrapper pattern intercept          |
                     |  - River ADWIN concept drift checks   |
                     +-------------------+-------------------+
                                         |
                                 (HTTP Telemetry)
                                         v
                     +-------------------+-------------------+
                     |       DriftGuard FastAPI Core API     | <---+ NextJS Dashboard (:3000)
                     |       - /register, /predict, /drift   | <---+ Grafana (:3001)
                     |       - Prom metrics /metrics (:8000) |
                     +-------------------+-------------------+
                                         |
                        (SLA Drift Breach Trigger)
                                         v
                     +-------------------+-------------------+
                     |      Prefect Orchestration Server     |
                     |      - drift_detection_flow (:4200)   |
                     +-------------------+-------------------+
                                         |
                                 (Runs steps)
                                         v
                     +-------------------+-------------------+
                     |      ZenML Step Training Pipelines    |
                     |  - Step 1: Great Expectations Validate|
                     |  - Step 2: Feast Feature Store Check  |
                     |  - Step 3: Train & Track (MLflow/W&B) |
                     |  - Step 4: Validate (>1% boost check) |
                     |  - Step 5: Canary Progressive Deploy  |
                     |  - Step 6: Immutable JSON Ledger & PDF|
                     +-------------------+-------------------+
                                         |
                            (Progressive Split Promotes)
                                         v
                     +-------------------+-------------------+
                     |       BentoML & Ray Serve Fleet       |
                     |       - canary_router: 10%->100%      |
                     |       - SLA Monitoring & Rollbacks    |
                     +---------------------------------------+
```

---

##  Prerequisites

To run and configure DriftGuard, ensure the following are installed:
- **Python 3.11** only (Ray and BentoML have incomplete 3.12 support).
- **Docker & Docker Compose** (for multi-service orchestration).
- **kubectl & Helm** (optional, for Kubernetes deployments).
- **HashiCorp Terraform** (optional, for AWS cloud provisioning).

---

##  Quick Start in 5 Lines

Wrap any scikit-learn, PyTorch, or HuggingFace model with DriftGuard SDK to track predictions, compute concept drift, and initiate auto-healing:

```python
from driftguard import DriftGuard

# 1. Initialize DriftGuard
dg = DriftGuard(model_id="fraud-detector-v1", api_url="http://localhost:8000", drift_threshold=0.15, auto_retrain=True)

# 2. Wrap model seamlessly
model = dg.wrap(trained_sklearn_model)

# 3. Predict normally - DriftGuard tracks inputs, outputs, and triggers retrain on drift!
prediction = model.predict(features)
```

---

## Installation & Setup

### 1. Local Package Installation
Clone the repository and install the DriftGuard package locally:
```bash
git clone https://github.com/your-repo/DriftGuard.git
cd DriftGuard
pip install -e .
```

To install validation pipelines dependencies (Great Expectations + SQLAlchemy 1.4 pin) separately:
```bash
pip install -e ".[validation]"
```

### 2. Launch Platform Services
Spin up the entire 8-service DriftGuard stack (FastAPI, NextJS dashboard, MLflow, Prefect, Postgres, Redis, Prometheus, Grafana) instantly:
```bash
docker-compose -f infra/docker-compose.yml up --build -d
```

---

##  SDK Configuration Parameters

The `DriftGuard` class accepts the following parameters:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `model_id` | `str` | *Required* | Unique name identifier of the model. |
| `api_url` | `str` | `http://localhost:8000` | Gateway endpoint of the DriftGuard API. |
| `drift_threshold` | `float` | `0.15` | Limit before concept drift alert and retraining triggers. |
| `auto_retrain` | `bool` | `True` | Automatically triggers retraining flow on threshold breach. |

---

##  API Gateway Documentation

DriftGuard Core API runs on port `8000`. Key REST endpoints include:

### `POST /register`
Registers a model for monitoring.
- **Request Body:**
  ```json
  {
    "model_id": "fraud-detector-v1",
    "drift_threshold": 0.15,
    "reference_data_path": "./data/baseline.parquet",
    "features": ["amount", "location_score", "velocity"]
  }
  ```
- **Response:** `{"status": "registered", "model_id": "fraud-detector-v1"}`

### `POST /predict/{model_id}`
SDK telemetry gateway recording prediction details and updating gauges.
- **Request Body:**
  ```json
  {
    "features": [1.2, 0.4, 9.8],
    "prediction": [1.0],
    "drift_score": 0.08
  }
  ```

### `GET /drift/{model_id}`
Fetches the last 100 historical drift scores for Recharts charts rendering.

### `POST /retrain/{model_id}`
Manually triggers the background retraining pipeline flow.

### `GET /metrics`
Exposes system health gauges for Prometheus scrapers in OpenMetrics format.

---

##  Dashboards & Observability Portals

Once the docker services are online:
1. **NextJS UI Dashboard:** Navigate to [http://localhost:3000](http://localhost:3000) to review models list, drift histories, vertical retraining timelines, and searchable audit logs.
2. **MLflow Registry:** Access [http://localhost:5000](http://localhost:5000) to review runs parameters, artifacts (confusion matrix plots), and staging/production champions.
3. **Prefect Dashboard:** Access [http://localhost:4200](http://localhost:4200) to inspect flows execution history.
4. **Grafana Dashboards:** Open [http://localhost:3001](http://localhost:3001) (User: `admin` | Pass: `admin`) to view pre-provisioned telemetry panels scraping predictions, drift rates, accuracy levels, and quantiles latency.

---

##  Running Unit Tests

Run all unit tests verifying ADWIN concept detectors, Great Expectations validators, canary routing splits, emergency rollbacks, and cryptographic audit log chains:
```bash
pytest tests/ -v
```

---

##  Deploying to AWS Cloud (Terraform)

Deploy DriftGuard core infrastructure to Amazon Web Services:
```bash
cd infra/terraform
terraform init
terraform plan
terraform apply -var="db_password=SecurePasswordPass22!"
```
This provisions:
- Amazon EKS cluster for progressive Kubernetes canary Rollouts.
- Amazon RDS PostgreSQL database for MLflow, Prefect, and platform metadata.
- Amazon ElastiCache Redis for online real-time Feast features access.
- Amazon S3 bucket for artifacts.
- Amazon ECR for Docker images.

# DriftGuard Regression Models Validation Report

This report presents validation results for the DriftGuard platform integrations against real-world regression models.

## 1. Summary Status
**Overall Validation Result: PASS**

## 2. Model Evaluation Details

### LinearRegression
* **Status**: PASS
* **Prediction Equality**: PASS
* **Telemetry Verification**: PASS (1001 records persisted)
* **Drift Detection**: PASS
* **Metrics Integrity (Original vs Wrapped)**:
  - **MAE**: Original=12.128280, Wrapped=12.128280
  - **RMSE**: Original=15.027778, Wrapped=15.027778
  - **R²**: Original=0.992299, Wrapped=0.992299
* **Scenario Performance Metrics (ADWIN global drift score)**:
  | Scenario | Average Drift Score | Max Drift Score |
  | :--- | :---: | :---: |
  | **Normal (X_test)** | 0.2506 | 0.3663 |
  | **Moderate (X_test * 1.5)** | 0.4256 | 0.5559 |
  | **Severe (X_test * 20.0)** | 0.9288 | 0.9632 |

### RandomForestRegressor
* **Status**: PASS
* **Prediction Equality**: PASS
* **Telemetry Verification**: PASS (1001 records persisted)
* **Drift Detection**: PASS
* **Metrics Integrity (Original vs Wrapped)**:
  - **MAE**: Original=27.115080, Wrapped=27.115080
  - **RMSE**: Original=36.083294, Wrapped=36.083294
  - **R²**: Original=0.955600, Wrapped=0.955600
* **Scenario Performance Metrics (ADWIN global drift score)**:
  | Scenario | Average Drift Score | Max Drift Score |
  | :--- | :---: | :---: |
  | **Normal (X_test)** | 0.2506 | 0.3663 |
  | **Moderate (X_test * 1.5)** | 0.4256 | 0.5559 |
  | **Severe (X_test * 20.0)** | 0.9288 | 0.9632 |

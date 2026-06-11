# DriftGuard Real Model Validation Report

This report presents validation results for the DriftGuard platform integrations against real scikit-learn classification models.

## 1. Summary Status
**Overall Validation Result: PASS**

## 2. Model Evaluation Details

### LogisticRegression
* **Status**: PASS
* **Prediction Equality (predict)**: PASS
* **Probability Equality (predict_proba)**: PASS
* **Drift Score Trend Assertion**: PASS
* **Telemetry Records Query Count**: 100 records persisted in DB
* **Scenario Performance Metrics**:
  | Scenario | Average Drift Score | Max Drift Score |
  | :--- | :---: | :---: |
  | **Normal (X_test)** | 0.3118 | 0.5615 |
  | **Moderate (X_test * 1.3)** | 0.5118 | 0.7231 |
  | **Severe (X_test * 20.0)** | 0.9830 | 0.9890 |

### RandomForestClassifier
* **Status**: PASS
* **Prediction Equality (predict)**: PASS
* **Probability Equality (predict_proba)**: PASS
* **Drift Score Trend Assertion**: PASS
* **Telemetry Records Query Count**: 100 records persisted in DB
* **Scenario Performance Metrics**:
  | Scenario | Average Drift Score | Max Drift Score |
  | :--- | :---: | :---: |
  | **Normal (X_test)** | 0.3118 | 0.5615 |
  | **Moderate (X_test * 1.3)** | 0.5118 | 0.7231 |
  | **Severe (X_test * 20.0)** | 0.9830 | 0.9890 |

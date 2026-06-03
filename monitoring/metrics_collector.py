"""
DriftGuard Prometheus Metrics Collector & Bridge.
Establishes system-wide Prometheus instrumentation for predictions, latencies, drift scores, and accuracy.
"""
import time
import logging
from typing import List, Dict, Any
from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger("DriftGuard.MetricsCollector")

# Define global collectors (registered on main.py startup)
# Standardize mapping to avoid duplicate registrations
try:
    predictions_counter = Counter(
        "driftguard_predictions_total",
        "Total predictions served by DriftGuard",
        ["model_id"]
    )
    drift_gauge = Gauge(
        "driftguard_drift_score",
        "Active running drift score computed",
        ["model_id", "feature_index"]
    )
    accuracy_gauge = Gauge(
        "driftguard_model_accuracy",
        "Model performance accuracy score",
        ["model_id", "version"]
    )
    retrain_counter = Counter(
        "driftguard_retraining_triggered_total",
        "Total model retraining loops initiated",
        ["model_id", "triggered_by"]
    )
    latency_histogram = Histogram(
        "driftguard_inference_latency_seconds",
        "Inference latency duration in seconds",
        ["model_id"]
    )
except ValueError:
    # Handle duplicate registration errors in local dev/tests cleanly
    from prometheus_client import REGISTRY
    predictions_counter = REGISTRY._names_to_collectors.get("driftguard_predictions_total")
    drift_gauge = REGISTRY._names_to_collectors.get("driftguard_drift_score")
    accuracy_gauge = REGISTRY._names_to_collectors.get("driftguard_model_accuracy")
    retrain_counter = REGISTRY._names_to_collectors.get("driftguard_retraining_triggered_total")
    latency_histogram = REGISTRY._names_to_collectors.get("driftguard_inference_latency_seconds")

def log_telemetry_metrics(
    model_id: str,
    feature_values: List[float],
    prediction_values: List[float],
    drift_score: float,
    latency_seconds: float = 0.0,
    model_version: str = "1.0.0"
):
    """
    Shorthand helper to update all live Prometheus metrics on a single prediction event.
    
    Args:
        model_id: Target model ID string.
        feature_values: Input features list.
        prediction_values: Output prediction list.
        drift_score: Computed concept drift score.
        latency_seconds: Recorded predict execution duration.
        model_version: Active model version label.
    """
    try:
        # Increment prediction counters
        predictions_counter.labels(model_id=model_id).inc()
        
        # Log drift scores per feature
        for idx, val in enumerate(feature_values):
            drift_gauge.labels(model_id=model_id, feature_index=str(idx)).set(drift_score)
            
        # Log latency if provided
        if latency_seconds > 0:
            latency_histogram.labels(model_id=model_id).observe(latency_seconds)
            
    except Exception as e:
        logger.warning(f"Failed to log metrics bridge: {e}")

def update_model_accuracy_metric(model_id: str, version: str, accuracy: float):
    """
    Updates the Prometheus accuracy gauge.
    """
    try:
        accuracy_gauge.labels(model_id=model_id, version=version).set(accuracy)
    except Exception as e:
        logger.warning(f"Failed to update accuracy gauge: {e}")

def increment_retraining_triggered_metric(model_id: str, triggered_by: str):
    """
    Increments the retraining counter.
    """
    try:
        retrain_counter.labels(model_id=model_id, triggered_by=triggered_by).inc()
    except Exception as e:
        logger.warning(f"Failed to increment retraining counter: {e}")

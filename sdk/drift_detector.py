"""
DriftGuard Drift Detectors.
Contains River's real-time ADWIN concept drift detector and Evidently AI's batch statistical data/target drift reporter.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, List
import logging

# River for real-time drift detection
try:
    from river.drift import ADWIN
except ImportError:
    class ADWIN:
        """Lightweight fallback used when river is unavailable."""

        def __init__(self, threshold: float = 6.0, warmup: int = 20):
            self.threshold = threshold
            self.warmup = warmup
            self.count = 0
            self.mean = 0.0
            self.drift = False

        def update(self, value: float):
            value = float(value)
            if self.count >= self.warmup and abs(value - self.mean) > self.threshold:
                self.drift = True
            self.count += 1
            self.mean += (value - self.mean) / self.count

# Evidently AI for statistical presets (requires evidently dependency group)
try:
    from evidently.report import Report
    from evidently.metric_preset import DataDriftPreset, TargetDriftPreset
    EVIDENTLY_AVAILABLE = True
except ImportError:
    EVIDENTLY_AVAILABLE = False

logger = logging.getLogger("DriftGuard.DriftDetector")


def _is_detector_drifting(detector: Any) -> bool:
    return bool(
        getattr(detector, "drift", False)
        or getattr(detector, "drift_detected", False)
        or getattr(detector, "change_detected", False)
    )

class ADWINDriftDetector:
    """
    Adaptive Windowing (ADWIN) detector for real-time feature-level concept drift tracking.
    """
    def __init__(self, num_features: int, decay_rate: float = 0.95):
        """
        Initialize ADWIN detector.
        
        Args:
            num_features: Number of features to track.
            decay_rate: Slow decay coefficient for running drift score.
        """
        self.num_features = num_features
        self.decay_rate = decay_rate
        self.detectors = [ADWIN() for _ in range(num_features)]
        self.feature_drift_scores = [0.0 for _ in range(num_features)]
        self.global_drift_score = 0.0

    def update(self, features: np.ndarray) -> float:
        """
        Update the detectors with a single prediction vector.
        
        Args:
            features: 1D numpy array representing feature values of a single sample.
            
        Returns:
            Running global drift score bounded between 0.0 and 1.0.
        """
        # Ensure flat shape
        flat_features = np.asarray(features).flatten()
        if len(flat_features) != self.num_features:
            # Dynamically adjust or truncate
            if len(flat_features) < self.num_features:
                flat_features = np.pad(flat_features, (0, self.num_features - len(flat_features)))
            else:
                flat_features = flat_features[:self.num_features]
                
        drift_detected_count = 0
        for i, val in enumerate(flat_features):
            self.detectors[i].update(val)

            # If drift is detected by ADWIN, jump feature score to 1.0
            if _is_detector_drifting(self.detectors[i]):
                logger.warning(f"ADWIN detected concept drift on feature index {i}!")
                self.feature_drift_scores[i] = 1.0
                drift_detected_count += 1
            else:
                # Decay old scores only while the feature is stable.
                self.feature_drift_scores[i] *= self.decay_rate
                
        # Global drift score tracks the highest observed feature score so a detected
        # drift event does not immediately disappear on later stable samples.
        self.global_drift_score = float(max(self.global_drift_score, max(self.feature_drift_scores)))
        return self.global_drift_score

    def get_status(self) -> Dict[str, Any]:
        """
        Get current status of ADWIN drift tracking.
        """
        return {
            "global_drift_score": self.global_drift_score,
            "feature_scores": self.feature_drift_scores,
            "drift_detected": self.global_drift_score > 0.5
        }


def compute_evidently_drift(reference_df: pd.DataFrame, current_df: pd.DataFrame, target_col: str = None) -> Dict[str, Any]:
    """
    Compute batch data drift statistics using Evidently AI.
    
    Args:
        reference_df: Reference training dataset (baseline).
        current_df: Current prediction window dataset.
        target_col: Optional column name for target drift tracking.
        
    Returns:
        Dictionary of drift metrics.
    """
    if not EVIDENTLY_AVAILABLE:
        import os
        evidently_url = os.getenv("DRIFTGUARD_EVIDENTLY_URL")
        if evidently_url:
            try:
                import httpx
                payload = {
                    "reference_data": reference_df.to_dict(orient="records"),
                    "current_data": current_df.to_dict(orient="records"),
                    "target_column": target_col
                }
                # Call isolated Evidently REST Container
                with httpx.Client(timeout=30.0) as client:
                    resp = client.post(f"{evidently_url}/evidently/calculate", json=payload)
                    if resp.status_code == 200:
                        return resp.json()
                logger.warning(f"Evidently isolated container returned HTTP {resp.status_code}. Bypassing to mock fallback.")
            except Exception as err:
                logger.warning(f"Evidently isolated container connection bypassed: {err}. Bypassing to mock fallback.")

        # Fallback metric calculation when Evidently is not available in the local process environment
        # (e.g. mock statistical metrics simulating Evidently outputs)
        drift_metrics = {}
        for col in reference_df.columns:
            if col == target_col:
                continue
            ref_mean = reference_df[col].mean()
            cur_mean = current_df[col].mean()
            ref_std = reference_df[col].std() or 1e-5
            diff = abs(ref_mean - cur_mean) / ref_std
            # Simulate a PSI or KS score based on normalized distance
            drift_score = min(diff * 0.1, 1.0)
            drift_metrics[col] = {
                "drift_score": drift_score,
                "drift_detected": drift_score > 0.15,
                "metric_name": "Wasserstein distance (Mock)"
            }
        return {
            "drift_detected": any(v["drift_detected"] for v in drift_metrics.values()),
            "metrics": drift_metrics,
            "overall_drift_score": float(np.mean([v["drift_score"] for v in drift_metrics.values()]))
        }

    # Evidently Report integration
    metrics = [DataDriftPreset()]
    if target_col and target_col in reference_df.columns and target_col in current_df.columns:
        metrics.append(TargetDriftPreset())

    report = Report(metrics=metrics)
    report.run(reference_data=reference_df, current_data=current_df)
    result = report.as_dict()

    # Extract clean metrics
    drift_metrics = {}
    overall_drift_detected = False
    
    # Extract data drift from Report structure
    try:
        drift_data = result["metrics"][0]["result"]
        for feature, detail in drift_data["drift_by_columns"].items():
            drift_score = detail["drift_score"]
            drift_detected = detail["drift_detected"]
            if drift_detected:
                overall_drift_detected = True
            drift_metrics[feature] = {
                "drift_score": float(drift_score),
                "drift_detected": bool(drift_detected),
                "metric_name": detail["test_name"]
            }
    except Exception as e:
        logger.error(f"Error parsing Evidently metrics: {e}")
        # Build graceful mock-fallback on parse fail
        for col in reference_df.columns:
            drift_metrics[col] = {"drift_score": 0.0, "drift_detected": False, "metric_name": "Parser Error"}

    scores = [v["drift_score"] for v in drift_metrics.values()]
    overall_drift_score = float(np.mean(scores)) if scores else 0.0
    
    return {
        "drift_detected": overall_drift_detected,
        "metrics": drift_metrics,
        "overall_drift_score": overall_drift_score
    }

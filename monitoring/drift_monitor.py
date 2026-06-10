"""
DriftGuard Sliding-Window Drift Monitor.
Periodically fetches a rolling window of recent prediction features from the database,
computes batch statistical drift via Evidently AI, and updates status metrics.
"""
import pandas as pd
import numpy as np
import datetime
import os
import json
import logging
from typing import Dict, Any

from driftguard.config import settings
from driftguard.drift_detector import compute_evidently_drift
from driftguard.alert import send_alert

logger = logging.getLogger("DriftGuard.DriftMonitor")

class SlidingWindowDriftMonitor:
    """
    Evaluates rolling prediction windows against reference data to identify statistical distributions shifts.
    """
    def __init__(self, model_id: str, db_session_maker: Any, window_size: int = 100):
        """
        Initialize the monitor.
        
        Args:
            model_id: Monitored model ID.
            db_session_maker: SQLAlchemy sessionmaker.
            window_size: Number of latest predictions to include in current evaluation window.
        """
        self.model_id = model_id
        self.db_session_maker = db_session_maker
        self.window_size = window_size

    def run_sliding_window_check(self) -> Dict[str, Any]:
        """
        Loads baseline reference data and latest predictions, executes Evidently reports,
        and saves outcomes to the database/alerts.
        """
        logger.info(f"[{self.model_id}] Starting rolling Evidently statistical drift check...")
        
        db = self.db_session_maker()
        try:
            # 1. Fetch Model definition
            from main import DBModel, DBPredictionLog, DBAuditLogEntry
            model = db.query(DBModel).filter(DBModel.model_id == self.model_id).first()
            if not model:
                logger.error(f"Model '{self.model_id}' not found in registry. Aborting check.")
                return {"status": "error", "message": "Model not registered"}

            # 2. Load reference dataset
            # If not configured, we create a synthetic baseline
            ref_path = model.reference_data_path
            if ref_path and os.path.exists(ref_path):
                try:
                    reference_df = pd.read_parquet(ref_path)
                except Exception as err:
                    logger.warning(f"Could not load parquet baseline: {err}. Using synthetic fallback.")
                    reference_df = self._generate_synthetic_baseline(model)
            else:
                reference_df = self._generate_synthetic_baseline(model)

            # Remove target column if exists
            if "target" in reference_df.columns:
                reference_df = reference_df.drop(columns=["target"])

            # 3. Load latest predictions from DB
            predictions = db.query(DBPredictionLog)\
                            .filter(DBPredictionLog.model_id == self.model_id)\
                            .order_by(DBPredictionLog.timestamp.desc())\
                            .limit(self.window_size)\
                            .all()

            if len(predictions) < 10:
                logger.info(f"Insufficient predictions logged ({len(predictions)}/10 min). Skipping check.")
                return {"status": "skipped", "message": "Insufficient logs"}

            # Build current window DataFrame
            feature_rows = []
            for pred in predictions:
                feat_list = json.loads(pred.features_json)
                feature_rows.append(feat_list)
                
            cols = [f"feature_{i}" for i in range(len(feature_rows[0]))]
            current_df = pd.DataFrame(feature_rows, columns=cols)

            # Truncate reference features if dimensions mismatch
            if len(reference_df.columns) != len(current_df.columns):
                # Sync column schemas
                reference_df = reference_df.iloc[:, :len(current_df.columns)]
                reference_df.columns = current_df.columns

            # 4. Compute Evidently statistical data drift
            drift_results = compute_evidently_drift(reference_df, current_df)
            overall_drift_score = drift_results.get("overall_drift_score", 0.0)
            drift_detected = drift_results.get("drift_detected", False)
            
            logger.info(f"Evidently computed overall drift score: {overall_drift_score:.4f} | Detected: {drift_detected}")

            # 5. Handle alert/status transitions
            if drift_detected or overall_drift_score > model.drift_threshold:
                if model.status != "retraining":
                    model.status = "degraded"
                    db.commit()
                    
                    # Log Audit entry
                    audit = DBAuditLogEntry(
                        model_id=self.model_id,
                        event_type="drift_detected",
                        model_version=model.version,
                        drift_score=overall_drift_score,
                        triggered_by="automatic",
                        details_json=json.dumps({
                            "message": f"Sliding window Evidently report detected data drift (score: {overall_drift_score:.4f}).",
                            "metrics_by_feature": drift_results.get("metrics", {})
                        })
                    )
                    db.add(audit)
                    db.commit()

                    # Trigger alert
                    send_alert(
                        event_type="drift_detected",
                        message=f"Statistical data drift detected on model '{self.model_id}' via sliding-window Evidently checks!",
                        details={
                            "model_id": self.model_id,
                            "overall_drift_score": f"{overall_drift_score:.4f}",
                            "threshold": f"{model.drift_threshold}"
                        }
                    )
                    
                    # Call retraining API
                    self._trigger_api_retraining(overall_drift_score)

            return {
                "status": "completed",
                "drift_score": overall_drift_score,
                "drift_detected": drift_detected,
                "metrics": drift_results.get("metrics", {})
            }

        except Exception as e:
            logger.error(f"Error executing sliding-window drift check: {e}")
            return {"status": "error", "error": str(e)}
        finally:
            db.close()

    def _generate_synthetic_baseline(self, model: Any) -> pd.DataFrame:
        """
        Creates elegant synthetic baseline dataframe when parquet is missing.
        """
        features_list = json.loads(model.features_json)
        num_features = len(features_list) if features_list else 5
        cols = [f"feature_{i}" for i in range(num_features)]
        
        # Seed stable normal distribution
        np.random.seed(42)
        data = np.random.normal(loc=0.0, scale=1.0, size=(100, num_features))
        return pd.DataFrame(data, columns=cols)

    def _trigger_api_retraining(self, drift_score: float):
        """
        Asynchronously sends POST request to trigger platform retraining.
        """
        import httpx
        import threading
        
        def call_endpoint():
            try:
                url = f"{settings.API_URL}/retrain/{self.model_id}"
                with httpx.Client(timeout=5.0) as client:
                    client.post(url, json={"drift_score": drift_score, "triggered_by": "automatic"})
            except Exception as e:
                logger.error(f"Failed to trigger auto-retraining: {e}")
                
        thread = threading.Thread(target=call_endpoint, daemon=True)
        thread.start()

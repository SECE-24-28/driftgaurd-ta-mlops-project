"""
DriftGuard SDK model tracking interceptor.
Provides the primary DriftGuard SDK client to wrap models and track real-time inputs, outputs, and concept drift.
"""
import time
import httpx
import numpy as np
import logging
from typing import Any, Union, Dict, List
import threading

from sdk.config import settings
from sdk.drift_detector import ADWINDriftDetector

logger = logging.getLogger("DriftGuard.SDK")

class DriftGuard:
    """
    DriftGuard SDK Client.
    Wraps existing machine learning models to intercept prediction requests,
    compute concept drift, and report stats to the central DriftGuard API.
    """
    def __init__(
        self,
        model_id: str,
        api_url: str = None,
        drift_threshold: float = None,
        auto_retrain: bool = True
    ):
        """
        Initialize the DriftGuard tracker.
        
        Args:
            model_id: Unique string identifier for the model.
            api_url: Address of the DriftGuard API. Defaults to environment config.
            drift_threshold: Target drift metric threshold. Defaults to environment config.
            auto_retrain: If True, triggers FastAPI retraining flows automatically on threshold breach.
        """
        self.model_id = model_id
        self.api_url = (api_url or settings.API_URL).rstrip("/")
        self.drift_threshold = drift_threshold if drift_threshold is not None else settings.DRIFT_THRESHOLD
        self.auto_retrain = auto_retrain
        
        # Will be initialized dynamically on the first prediction call based on feature dimensions
        self.drift_detector = None
        self.retraining_triggered = False
        
        logger.info(f"Initialized DriftGuard SDK for model '{model_id}' against API: {self.api_url}")

    def wrap(self, model: Any) -> "DriftGuardModelWrapper":
        """
        Wrap any machine learning model to automatically track its inputs and outputs.
        
        Args:
            model: An arbitrary model instance (scikit-learn, PyTorch, HuggingFace, etc.)
            
        Returns:
            A wrapped model interceptor.
        """
        return DriftGuardModelWrapper(model, self)

    def _send_telemetry_async(self, features: list, prediction: list, drift_score: float):
        """
        Internal helper to send model inputs/predictions to DriftGuard API asynchronously.
        """
        def send():
            try:
                # Fire and forget POST request to DriftGuard backend
                url = f"{self.api_url}/predict/{self.model_id}"
                payload = {
                    "features": features,
                    "prediction": prediction,
                    "drift_score": drift_score
                }
                with httpx.Client(timeout=2.0) as client:
                    resp = client.post(url, json=payload)
                    if resp.status_code == 200:
                        logger.debug("Successfully logged prediction telemetry to DriftGuard API")
                    else:
                        logger.warning(f"Failed to log prediction: API returned {resp.status_code}")
            except Exception as e:
                logger.debug(f"DriftGuard API telemetry connection bypassed: {e}")

        thread = threading.Thread(target=send, daemon=True)
        thread.start()

    def _trigger_retraining_async(self, current_drift_score: float):
        """
        Triggers retraining pipeline via FastAPI endpoint.
        """
        if self.retraining_triggered:
            return  # Prevent double trigger

        self.retraining_triggered = True

        def trigger():
            try:
                url = f"{self.api_url}/retrain/{self.model_id}"
                payload = {
                    "drift_score": current_drift_score,
                    "triggered_by": "automatic"
                }
                logger.info(f"Drift threshold exceeded ({current_drift_score:.4f} > {self.drift_threshold}). Triggering auto-retraining...")
                with httpx.Client(timeout=5.0) as client:
                    resp = client.post(url, json=payload)
                    if resp.status_code == 200:
                        logger.info("Successfully triggered autonomous retraining pipeline!")
                    else:
                        logger.error(f"Retrain endpoint returned error: {resp.status_code}")
            except Exception as e:
                logger.error(f"Failed to reach DriftGuard retrain endpoint: {e}")
                # Reset trigger flag so we can retry on next predictions
                self.retraining_triggered = False

        thread = threading.Thread(target=trigger, daemon=True)
        thread.start()


class DriftGuardModelWrapper:
    """
    Model interceptor wrapping target models and forwarding calls while computing drift metrics.
    """
    def __init__(self, model: Any, tracker: DriftGuard):
        self._model = model
        self._tracker = tracker

    def predict(self, features: Any, *args, **kwargs) -> Any:
        """
        Intercept standard scikit-learn/sklearn predict calls.
        """
        prediction = self._forward_predict(features, *args, **kwargs)
        self._track(features, prediction)
        return prediction

    def __call__(self, features: Any, *args, **kwargs) -> Any:
        """
        Intercept direct callable objects (e.g., PyTorch models, HuggingFace pipelines).
        """
        prediction = self._forward_call(features, *args, **kwargs)
        self._track(features, prediction)
        return prediction

    def predict_proba(self, features: Any, *args, **kwargs) -> Any:
        """
        Intercept predict_proba.
        """
        # Forward call
        if hasattr(self._model, "predict_proba"):
            return self._model.predict_proba(features, *args, **kwargs)
        raise AttributeError(f"Wrapped model does not expose predict_proba.")

    def _forward_predict(self, features: Any, *args, **kwargs) -> Any:
        if hasattr(self._model, "predict"):
            return self._model.predict(features, *args, **kwargs)
        elif callable(self._model):
            return self._model(features, *args, **kwargs)
        else:
            raise AttributeError("Wrapped model does not have a predict method or __call__ function.")

    def _forward_call(self, features: Any, *args, **kwargs) -> Any:
        if callable(self._model):
            return self._model(features, *args, **kwargs)
        elif hasattr(self._model, "predict"):
            return self._model.predict(features, *args, **kwargs)
        else:
            raise AttributeError("Wrapped model does not have a predict method or __call__ function.")

    def _track(self, features: Any, prediction: Any):
        """
        Tracks prediction request details, runs ADWIN checks and notifies platform.
        """
        try:
            # 1. Standardize features to float array/list
            # Handle numpy arrays, dataframes, PyTorch tensors, or list inputs
            feat_arr = self._to_numpy_array(features)
            pred_arr = self._to_numpy_array(prediction)
            
            # If flat 1D, make it 2D (batch of 1)
            if feat_arr.ndim == 1:
                feat_arr = feat_arr.reshape(1, -1)
            if pred_arr.ndim == 0 or pred_arr.ndim == 1:
                pred_arr = pred_arr.reshape(1, -1)

            # Extract dimensions
            num_samples, num_features = feat_arr.shape
            
            # Initialize ADWIN detector on first call if not present
            if self._tracker.drift_detector is None:
                self._tracker.drift_detector = ADWINDriftDetector(num_features=num_features)

            # 2. Iterate samples to update River ADWIN detector
            drift_score = 0.0
            for i in range(num_samples):
                sample_features = feat_arr[i]
                drift_score = self._tracker.drift_detector.update(sample_features)

            # 3. Log values to API backend
            # Convert first sample features and prediction to list for JSON serialization
            self._tracker._send_telemetry_async(
                features=feat_arr[0].tolist(),
                prediction=pred_arr[0].tolist(),
                drift_score=drift_score
            )

            # 4. Check for drift threshold breach
            if drift_score > self._tracker.drift_threshold and self._tracker.auto_retrain:
                self._tracker._trigger_retraining_async(drift_score)

        except Exception as e:
            # SDK should never crash user prediction loop
            logger.error(f"DriftGuard tracking encountered an internal warning: {e}")

    def _to_numpy_array(self, data: Any) -> np.ndarray:
        """
        Safely convert standard containers (lists, numpy, pandas, PyTorch) to a numpy array.
        """
        # Handle string or dictionary text classifications
        if isinstance(data, (str, dict)):
            # Mock hash array or vector length of 1 for string payloads (e.g. HuggingFace)
            return np.array([hash(str(data)) % 1000 / 1000.0], dtype=np.float32)
            
        # Handle HuggingFace pipeline response lists
        if isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
            # Extract scores or labels from e.g. [{"label": "POSITIVE", "score": 0.99}]
            extracted = []
            for item in data:
                val = item.get("score", 0.0) if isinstance(item, dict) else 0.0
                extracted.append(val)
            return np.array(extracted, dtype=np.float32)

        # PyTorch Tensor check
        if hasattr(data, "detach") and hasattr(data, "cpu"):
            data = data.detach().cpu().numpy()
            
        # Pandas DataFrame check
        if hasattr(data, "values"):
            data = data.values

        # Convert to numpy array safely
        try:
            return np.asarray(data, dtype=np.float32)
        except Exception:
            # Fallback for complex structure string mappings
            return np.array([0.0], dtype=np.float32)

    def __getattr__(self, name):
        """
        Delegate remaining calls directly to the target model.
        """
        return getattr(self._model, name)

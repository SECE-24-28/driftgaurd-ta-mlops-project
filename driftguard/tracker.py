"""
DriftGuard SDK model tracking interceptor.
Provides the primary DriftGuard SDK client to wrap models and track real-time inputs, outputs, and concept drift.
"""
import os
import time
import httpx
import numpy as np
import logging
from typing import Any, Callable, Dict, List, Optional, Union
import threading
import queue
import atexit

from driftguard.config import settings
from driftguard.drift_detector import ADWINDriftDetector

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
        api_key: str = None,
        project_id: int = None,
        drift_threshold: float = None,
        auto_retrain: bool = True
    ):
        """
        Initialize the DriftGuard tracker.
        
        Args:
            model_id: Unique string identifier for the model.
            api_url: Address of the DriftGuard API. Defaults to environment config.
            api_key: User API key for SaaS authentication.
            project_id: Project scope ID for multi-tenant isolation.
            drift_threshold: Target drift metric threshold. Defaults to environment config.
            auto_retrain: If True, triggers FastAPI retraining flows automatically on threshold breach.
        """
        import os
        self.model_id = model_id
        self.api_url = (api_url or settings.API_URL).rstrip("/")
        self.api_key = api_key or os.getenv("DRIFTGUARD_API_KEY")
        
        proj_env = os.getenv("DRIFTGUARD_PROJECT_ID")
        self.project_id = project_id if project_id is not None else (int(proj_env) if proj_env else None)
        self.drift_threshold = drift_threshold if drift_threshold is not None else settings.DRIFT_THRESHOLD
        self.auto_retrain = auto_retrain

        # Drift detector — initialized lazily on first predict call
        self.drift_detector = None
        self.retraining_triggered = False

        # ── Callback registry ────────────────────────────────────────────
        # Set by @dg.retrainer decorator
        self._retrainer_fn: Optional[Callable] = None
        # Set by dg.set_champion(model) — used for champion/challenger comparison
        self._champion_model: Optional[Any] = None
        # Set by dg.set_validation_data(X, y) — used inside CallbackRunner validation
        self._validation_features: Optional[Any] = None
        self._validation_labels: Optional[Any] = None

        # Auto-restore champion model from disk if version matches
        if self.project_id and self.api_key:
            try:
                import joblib
                headers = {"X-API-Key": self.api_key}
                with httpx.Client(timeout=2.0) as client:
                    resp = client.get(f"{self.api_url}/models/{self.model_id}", headers=headers)
                    if resp.status_code == 200:
                        version = resp.json().get("version", "1.0.0")
                        file_path = os.path.join(
                            settings.ARTIFACT_ROOT,
                            str(self.project_id),
                            self.model_id,
                            f"version_{version}.pkl"
                        )
                        if os.path.exists(file_path):
                            self._champion_model = joblib.load(file_path)
                            logger.info(f"[{self.model_id}] Auto-restored champion model version {version} from {file_path}")
            except Exception as e:
                logger.debug(f"[{self.model_id}] Could not auto-restore champion model: {e}")

        # Telemetry Queue & Worker setup
        self._telemetry_queue = queue.Queue(maxsize=15000)
        self.telemetry_queued = 0
        self.telemetry_sent = 0
        self.telemetry_failed = 0
        self._is_shutdown = False
        self._telemetry_stop_event = threading.Event()
        self._telemetry_worker = threading.Thread(
            target=self._telemetry_worker_loop,
            daemon=True,
            name=f"driftguard-telemetry-worker-{self.model_id}"
        )
        self._telemetry_worker.start()
        atexit.register(self._shutdown_telemetry_worker)

        logger.info(f"Initialized DriftGuard SDK for model '{model_id}' against API: {self.api_url}")

    def wrap(self, model: Any) -> "DriftGuardModelWrapper":
        """
        Wrap any machine learning model to automatically track its inputs and outputs.

        Args:
            model: An arbitrary model instance (scikit-learn, PyTorch, HuggingFace, etc.)

        Returns:
            A DriftGuardModelWrapper interceptor.
        """
        return DriftGuardModelWrapper(model, self)

    # ------------------------------------------------------------------
    # Callback registration API
    # ------------------------------------------------------------------

    def retrainer(self, fn: Callable) -> Callable:
        """
        Decorator that registers a user-defined retraining callback.

        The decorated function must:
        - Accept no arguments.
        - Return a trained model object (scikit-learn, PyTorch, etc.).
        - Load training data from a **trusted source** (not production telemetry).

        Example::

            @dg.retrainer
            def retrain():
                df = pd.read_parquet("s3://my-bucket/training/latest.parquet")
                X, y = df.drop("label", axis=1), df["label"]
                clf = RandomForestClassifier(n_estimators=200)
                clf.fit(X, y)
                return clf

        When drift exceeds ``drift_threshold``, DriftGuard invokes this
        callback inside a daemon thread, validates the returned model against
        the champion, and promotes it if it wins.
        """
        if not callable(fn):
            raise TypeError(
                f"@dg.retrainer expects a callable, got {type(fn).__name__!r}."
            )
        self._retrainer_fn = fn
        logger.info(
            f"[{self.model_id}] Retrainer callback registered: '{fn.__name__}()'"
        )
        return fn

    def set_champion(self, model: Any) -> None:
        """
        Register the current production champion model.

        Used during champion/challenger validation: the challenger returned
        by ``@dg.retrainer`` must outperform this model by at least 1%
        (on the dataset provided via ``set_validation_data``) to be promoted.

        Call this with the same model object you pass to ``dg.wrap()``.

        Args:
            model: The current production model object.
        """
        self._champion_model = model
        logger.info(f"[{self.model_id}] Champion model registered for comparison.")
        if self.project_id:
            try:
                import joblib
                version = "1.0.0"
                if self.api_key:
                    try:
                        headers = {"X-API-Key": self.api_key}
                        with httpx.Client(timeout=2.0) as client:
                            resp = client.get(f"{self.api_url}/models/{self.model_id}", headers=headers)
                            if resp.status_code == 200:
                                version = resp.json().get("version", "1.0.0")
                    except Exception:
                        pass
                # Use absolute ARTIFACT_ROOT so artifacts are written to the same
                # location regardless of the script's working directory.
                dir_path = os.path.join(
                    settings.ARTIFACT_ROOT,
                    str(self.project_id),
                    self.model_id
                )
                os.makedirs(dir_path, exist_ok=True)
                file_path = os.path.join(dir_path, f"version_{version}.pkl")
                joblib.dump(model, file_path)
                logger.info(f"[{self.model_id}] Persisted champion model to {file_path}")
            except Exception as e:
                logger.warning(f"[{self.model_id}] Failed to persist champion model: {e}")

    def set_validation_data(self, features: Any, labels: Any) -> None:
        """
        Register a held-out validation dataset for champion/challenger comparison.

        This dataset must come from a **trusted source** (e.g., a curated
        evaluation set), never from live production telemetry.

        Args:
            features: Feature matrix — numpy array, pandas DataFrame, or list.
            labels:   Ground-truth label array — numpy array or list.
        """
        import numpy as np
        self._validation_features = np.asarray(features, dtype=np.float32)
        self._validation_labels = np.asarray(labels)
        logger.info(
            f"[{self.model_id}] Validation dataset registered: "
            f"{len(self._validation_features)} samples."
        )

    def _send_telemetry_async(self, features: list, prediction: list, drift_score: float):
        """
        Puts telemetry payload onto the queue for asynchronous logging.
        Drops data under queue overflow to prevent latency spikes in the prediction loop.
        """
        if self._is_shutdown:
            logger.warning(f"[{self.model_id}] Telemetry tracker has been shut down. Rejecting new payload.")
            return
        payload = {
            "features": features,
            "prediction": prediction,
            "drift_score": drift_score
        }
        self.telemetry_queued += 1
        try:
            self._telemetry_queue.put_nowait(payload)
        except queue.Full:
            self.telemetry_failed += 1
            import sys
            print(f"[DriftGuard SDK] Telemetry queue full. Dropping payload to prevent model latency spike.", file=sys.stderr)
            logger.warning(
                f"[{self.model_id}] Telemetry queue full. "
                "Dropping telemetry payload to prevent model prediction latency spike."
            )

    def _telemetry_worker_loop(self):
        """
        Dedicated telemetry consumer worker.
        Uses a single persistent HTTP client connection pool for TCP socket reuse.
        """
        headers = {"X-API-Key": self.api_key} if self.api_key else {}
        url = f"{self.api_url}/predict/{self.model_id}"
        
        client = httpx.Client(timeout=5.0)
        try:
            while not self._telemetry_stop_event.is_set() or not self._telemetry_queue.empty():
                try:
                    # Fetch next payload; short timeout so we check stop_event periodically
                    payload = self._telemetry_queue.get(timeout=0.2)
                except queue.Empty:
                    continue
                
                # Attempt to upload telemetry with retry logic
                success = False
                terminal_fail = False
                for attempt in range(5):
                    try:
                        resp = client.post(url, json=payload, headers=headers)
                        if resp.status_code == 200:
                            success = True
                            self.telemetry_sent += 1
                            break
                        elif resp.status_code == 401:
                            print(f"[DriftGuard SDK] Telemetry failed: 401 Unauthorized")
                            self.telemetry_failed += 1
                            terminal_fail = True
                            break
                        else:
                            print(f"[DriftGuard SDK] Telemetry upload failed (HTTP {resp.status_code}). Attempt {attempt + 1}/5")
                    except (httpx.ConnectError, httpx.RemoteProtocolError, httpx.WriteError, httpx.ReadError) as err:
                        print(f"[DriftGuard SDK] Telemetry connection error: {err}. Recreating connection pool. Attempt {attempt + 1}/5")
                        try:
                            client.close()
                        except Exception:
                            pass
                        client = httpx.Client(timeout=5.0)
                    except Exception as err:
                        print(f"[DriftGuard SDK] Telemetry error: {err}. Attempt {attempt + 1}/5")
                    time.sleep(0.05 * (attempt + 1))  # exponential backoff
                
                if not success and not terminal_fail:
                    self.telemetry_failed += 1
                self._telemetry_queue.task_done()
        finally:
            try:
                client.close()
            except Exception:
                pass

    def shutdown(self, timeout: float = 30.0):
        """
        Gracefully shut down the telemetry tracker:
        - Stop accepting new telemetry payloads
        - Wait for any remaining items in the queue to be processed (drain)
        - Signal worker to stop
        - Join the worker thread (which guarantees HTTP client/session is closed cleanly)
        """
        if self._is_shutdown:
            return
            
        logger.info(f"[{self.model_id}] Initiating graceful SDK telemetry shutdown...")
        self._is_shutdown = True
        
        # Signal stop event
        self._telemetry_stop_event.set()
        
        # Wait for worker thread to finish (it will process the remaining queue items before stopping)
        if self._telemetry_worker.is_alive():
            logger.info(f"[{self.model_id}] Flushing telemetry queue ({self._telemetry_queue.qsize()} items) and waiting for worker thread...")
            self._telemetry_worker.join(timeout=timeout)
            if self._telemetry_worker.is_alive():
                logger.warning(f"[{self.model_id}] Telemetry worker did not stop within {timeout}s timeout.")
            else:
                logger.info(f"[{self.model_id}] Telemetry worker stopped successfully.")
                
        logger.info(f"[{self.model_id}] Graceful shutdown complete. Queued: {self.telemetry_queued}, Sent: {self.telemetry_sent}, Failed: {self.telemetry_failed}")

    def _shutdown_telemetry_worker(self):
        """
        Graceful shutdown hook. Set stop event and flush remaining queue items.
        """
        self.shutdown(timeout=5.0)

    def _trigger_retraining_async(self, current_drift_score: float) -> None:
        """
        Trigger model retraining in a background thread.

        Branching logic
        ---------------
        * If a callback was registered via ``@dg.retrainer``: run the full
          SDK-side pipeline. Thread is NON-DAEMON so the process waits for
          it to complete before exiting.
        * Otherwise: server-side fallback via POST /retrain (daemon thread,
          fire-and-forget).
        """
        if self.retraining_triggered:
            logger.debug(f"[{self.model_id}] _trigger_retraining_async: already triggered, skipping.")
            return

        self.retraining_triggered = True
        logger.info(
            f"[{self.model_id}] Drift threshold exceeded "
            f"({current_drift_score:.4f} > {self.drift_threshold}). "
            f"Triggering auto-retraining "
            f"({'callback' if self._retrainer_fn else 'server-side'} path)..."
        )

        if self._retrainer_fn is not None:
            # ── SDK-side callback pipeline ────────────────────────────────
            # IMPORTANT: thread must NOT be daemon=True.
            # A daemon thread is killed the moment the main thread exits.
            # If the predict() loop finishes before the thread completes,
            # the callback will never fire. Use daemon=False so Python waits.
            def _run_callback_pipeline() -> None:
                print("[DriftGuard] CALLBACK THREAD STARTED")
                try:
                    from driftguard.callback_runner import RetrainerCallbackRunner
                    runner = RetrainerCallbackRunner(self)
                    runner.run(current_drift_score)
                except Exception as exc:
                    import sys
                    print(f"[DriftGuard] CALLBACK THREAD ERROR: {exc}", file=sys.stderr)
                    logger.error(f"Callback pipeline thread crashed: {exc}", exc_info=True)
                    self.retraining_triggered = False

            thread = threading.Thread(
                target=_run_callback_pipeline,
                daemon=False,
                name=f"driftguard-retrain-{self.model_id}",
            )
            thread.start()
            logger.info(f"[{self.model_id}] Callback thread started: {thread.name}")

        else:
            # ── Server-side fallback (original behaviour, fire-and-forget) ──
            def _trigger_server() -> None:
                try:
                    url = f"{self.api_url}/retrain/{self.model_id}"
                    payload = {
                        "drift_score": current_drift_score,
                        "triggered_by": "automatic",
                        "source": "server",
                    }
                    headers = {"X-API-Key": self.api_key} if self.api_key else {}
                    with httpx.Client(timeout=5.0) as client:
                        resp = client.post(url, json=payload, headers=headers)
                        if resp.status_code == 200:
                            logger.info(
                                f"[{self.model_id}] Server-side retraining pipeline triggered."
                            )
                        else:
                            logger.error(
                                f"[{self.model_id}] /retrain returned HTTP {resp.status_code}"
                            )
                except Exception as exc:
                    logger.error(
                        f"[{self.model_id}] Failed to reach retrain endpoint: {exc}"
                    )
                    self.retraining_triggered = False

            thread = threading.Thread(target=_trigger_server, daemon=True)
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
                ref = self._tracker._validation_features  # may be None
                self._tracker.drift_detector = ADWINDriftDetector(
                    num_features=num_features,
                    reference_data=ref,
                )
                logger.debug(
                    f"[{self._tracker.model_id}] ADWIN initialized: {num_features} features, "
                    f"threshold={self._tracker.drift_threshold}, "
                    f"reference_samples={len(ref) if ref is not None else 0}"
                )

            # 2. Iterate samples to update ADWIN detector
            drift_score = 0.0
            for i in range(num_samples):
                sample_features = feat_arr[i]
                drift_score = self._tracker.drift_detector.update(sample_features)

            logger.debug(
                f"[{self._tracker.model_id}] drift_score={drift_score:.6f} "
                f"threshold={self._tracker.drift_threshold} "
                f"triggered={self._tracker.retraining_triggered}"
            )

            # 3. Upload telemetry asynchronously
            self._tracker._send_telemetry_async(
                features=feat_arr[0].tolist(),
                prediction=pred_arr[0].tolist(),
                drift_score=drift_score
            )

            # 4. Check for drift threshold breach
            if drift_score > self._tracker.drift_threshold and self._tracker.auto_retrain:
                logger.info(
                    f"[{self._tracker.model_id}] Drift threshold breached "
                    f"({drift_score:.6f} > {self._tracker.drift_threshold}) — triggering retraining."
                )
                self._tracker._trigger_retraining_async(drift_score)

        except Exception as exc:
            # Never crash the user's prediction loop, but ALWAYS surface the error
            import sys
            print(f"[DriftGuard] ERROR inside _track(): {exc}", file=sys.stderr)
            logger.error(f"DriftGuard tracking error: {exc}", exc_info=True)

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

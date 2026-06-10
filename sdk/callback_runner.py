"""
DriftGuard Retrainer Callback Runner.

Executes user-registered ``@dg.retrainer`` callbacks entirely inside the
SDK process — where the user's data, credentials, and environment live.

Flow
----
1. Notify API: POST /retrain/{model_id} with source="sdk_callback"
   → Server creates a DBRetrainingEvent record and returns event_id.
   → Server does NOT spawn its own background pipeline.
2. Invoke the user's retrainer function → get challenger model.
3. Validate challenger vs champion using dg.set_validation_data().
4. Report outcome: POST /retrain/{model_id}/complete.
   → Server updates model version, accuracy, audit log, Prometheus, Slack.
5. Update tracker._champion_model to the new champion.
6. Reset tracker.retraining_triggered so future drift events can fire.

NOTE: Production telemetry stored in dg_predictions is never touched.
      Training data comes exclusively from the user's registered callback.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Optional, Tuple

import httpx

if TYPE_CHECKING:
    from sdk.tracker import DriftGuard

logger = logging.getLogger("DriftGuard.CallbackRunner")


class RetrainerCallbackRunner:
    """
    Orchestrates the full local retraining pipeline for a registered callback.

    Parameters
    ----------
    tracker:
        The ``DriftGuard`` instance that owns the callback.
    """

    def __init__(self, tracker: "DriftGuard") -> None:
        self.tracker = tracker
        self.api_url = tracker.api_url
        self.model_id = tracker.model_id

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def run(self, drift_score: float) -> bool:
        """
        Execute the full callback-based retraining pipeline.

        Returns
        -------
        bool
            ``True`` if the challenger was promoted; ``False`` otherwise.
        """
        logger.info(
            f"[{self.model_id}] Callback retraining pipeline started "
            f"(drift_score={drift_score:.4f})"
        )

        # Step 1 — Record event on the server (no background task spawned)
        current_version = self._get_current_version()
        event_id = self._notify_retrain_start(drift_score)

        try:
            # Step 2 — Invoke user-registered callback
            challenger_model = self._invoke_callback()

            # Step 3 — Validate challenger against champion
            validation_passed, champ_score, chall_score = self._validate(challenger_model)

            if not validation_passed:
                reason = (
                    f"Challenger accuracy {chall_score:.4f} did not beat "
                    f"champion {champ_score:.4f} by ≥1%."
                )
                logger.warning(f"[{self.model_id}] {reason}")
                self._report_failure(event_id=event_id, reason=reason, chall_score=chall_score)
                return False

            # Step 4 — Promote challenger
            new_version = self._bump_version(current_version)
            self._report_success(
                event_id=event_id,
                new_version=new_version,
                new_accuracy=chall_score,
                old_accuracy=champ_score,
            )

            # Step 5 — Update local champion reference so next comparison is correct
            self.tracker._champion_model = challenger_model

            logger.info(
                f"[{self.model_id}] Challenger promoted: "
                f"{current_version} → {new_version}  "
                f"(accuracy {champ_score:.4f} → {chall_score:.4f})"
            )
            return True

        except Exception as exc:
            logger.error(
                f"[{self.model_id}] Callback retraining pipeline failed: {exc}",
                exc_info=True,
            )
            self._report_failure(event_id=event_id, reason=str(exc), chall_score=0.0)
            return False

        finally:
            # Always reset so future drift events can trigger a new run
            self.tracker.retraining_triggered = False

    # ------------------------------------------------------------------
    # Step implementations
    # ------------------------------------------------------------------

    def _invoke_callback(self) -> Any:
        """
        Call the user's ``@dg.retrainer`` function and return the trained model.

        Raises
        ------
        RuntimeError
            If the callback raises or returns ``None``.
        """
        fn = self.tracker._retrainer_fn
        logger.info(f"[{self.model_id}] Invoking retrainer callback: {fn.__name__}()")
        try:
            model = fn()
        except Exception as exc:
            raise RuntimeError(
                f"Retrainer callback '{fn.__name__}' raised an exception: {exc}"
            ) from exc

        if model is None:
            raise ValueError(
                f"Retrainer callback '{fn.__name__}' returned None. "
                "The function must return a trained model object."
            )
        if not (hasattr(model, "predict") or callable(model)):
            raise TypeError(
                f"Retrainer callback '{fn.__name__}' returned an invalid model type '{type(model).__name__}'. "
                "The model must have a 'predict' method or be callable."
            )
        return model

    def _validate(self, challenger_model: Any) -> Tuple[bool, float, float]:
        """
        Compare challenger against the current champion.

        If ``dg.set_champion()`` has not been called, the challenger is
        promoted directly as the first known-good version.

        If ``dg.set_validation_data()`` has not been called, validation is
        skipped and the challenger is promoted with a warning.

        Returns
        -------
        (validation_passed, champion_score, challenger_score)
        """
        champion_model = self.tracker._champion_model

        if champion_model is None:
            logger.info(
                f"[{self.model_id}] No champion registered via dg.set_champion(). "
                "Promoting challenger as first champion."
            )
            return True, 0.0, 1.0

        val_features = self.tracker._validation_features
        val_labels = self.tracker._validation_labels

        if val_features is None or val_labels is None:
            logger.warning(
                f"[{self.model_id}] No validation data registered via "
                "dg.set_validation_data(). Promoting without accuracy comparison."
            )
            return True, 0.0, 1.0

        from pipeline.validate_pipeline import validate_challenger_vs_champion

        return validate_challenger_vs_champion(
            champion_model=champion_model,
            challenger_model=challenger_model,
            val_features=val_features,
            val_labels=val_labels,
            threshold_pct=0.01,  # challenger must beat champion by ≥1%
        )

    # ------------------------------------------------------------------
    # API notification helpers
    # ------------------------------------------------------------------

    def _get_current_version(self) -> str:
        """Fetch the model's current version string from the API."""
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.get(f"{self.api_url}/models/{self.model_id}")
                if resp.status_code == 200:
                    return resp.json().get("version", "1.0.0")
        except Exception as exc:
            logger.debug(f"[{self.model_id}] Could not fetch current version: {exc}")
        return "1.0.0"

    def _bump_version(self, current_version: str) -> str:
        """Increment the patch segment of a semantic version string."""
        try:
            parts = current_version.split(".")
            parts[-1] = str(int(parts[-1]) + 1)
            return ".".join(parts)
        except Exception:
            return "1.0.1"

    def _notify_retrain_start(self, drift_score: float) -> Optional[int]:
        """
        POST to ``/retrain/{model_id}`` with ``source="sdk_callback"``.

        The server records the event and returns an ``event_id`` but does
        NOT spawn its own background retraining task.
        """
        try:
            with httpx.Client(timeout=5.0) as client:
                resp = client.post(
                    f"{self.api_url}/retrain/{self.model_id}",
                    json={
                        "drift_score": drift_score,
                        "triggered_by": "automatic",
                        "source": "sdk_callback",
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    event_id = data.get("event_id")
                    logger.debug(
                        f"[{self.model_id}] Retrain event created, event_id={event_id}"
                    )
                    return event_id
                logger.warning(
                    f"[{self.model_id}] /retrain returned HTTP {resp.status_code}"
                )
        except Exception as exc:
            logger.warning(
                f"[{self.model_id}] Could not notify API of retrain start: {exc}"
            )
        return None

    def _report_success(
        self,
        event_id: Optional[int],
        new_version: str,
        new_accuracy: float,
        old_accuracy: float,
    ) -> None:
        """POST callback pipeline results to ``/retrain/{model_id}/complete``."""
        try:
            with httpx.Client(timeout=10.0) as client:
                client.post(
                    f"{self.api_url}/retrain/{self.model_id}/complete",
                    json={
                        "event_id": event_id,
                        "validation_passed": True,
                        "new_version": new_version,
                        "new_accuracy": new_accuracy,
                        "old_accuracy": old_accuracy,
                        "error": None,
                    },
                )
        except Exception as exc:
            logger.warning(
                f"[{self.model_id}] Could not report retrain success to API: {exc}"
            )

    def _report_failure(
        self,
        event_id: Optional[int],
        reason: str,
        chall_score: float,
    ) -> None:
        """Report a failed callback pipeline to ``/retrain/{model_id}/complete``."""
        try:
            with httpx.Client(timeout=10.0) as client:
                client.post(
                    f"{self.api_url}/retrain/{self.model_id}/complete",
                    json={
                        "event_id": event_id,
                        "validation_passed": False,
                        "new_version": None,
                        "new_accuracy": chall_score,
                        "old_accuracy": None,
                        "error": reason,
                    },
                )
        except Exception as exc:
            logger.warning(
                f"[{self.model_id}] Could not report retrain failure to API: {exc}"
            )

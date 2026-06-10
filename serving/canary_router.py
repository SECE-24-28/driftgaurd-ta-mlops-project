"""
DriftGuard Canary Request Router.
Splits incoming model prediction requests between champion and challenger models based on weight settings.
Logs choices in the audit trail for governance traceability.
"""
import os
import random
import logging
from typing import Dict, Any, Tuple

from driftguard.config import settings
from governance.audit_log import write_audit_entry

logger = logging.getLogger("DriftGuard.CanaryRouter")

def get_canary_split_weight() -> float:
    """
    Parses active canary weight split from environment.
    
    Returns:
        A float weight between 0.0 and 1.0 representing Challenger's traffic portion.
    """
    # Check environment override
    weight_str = os.getenv("DRIFTGUARD_CANARY_SPLIT", "")
    if not weight_str:
        return settings.CANARY_INITIAL_WEIGHT
    try:
        weight = float(weight_str)
        return max(0.0, min(1.0, weight))
    except ValueError:
        return settings.CANARY_INITIAL_WEIGHT

def route_canary_prediction(
    features: Any,
    champion_model: Any,
    challenger_model: Any,
    model_id: str,
    challenger_version: str = "1.0.5"
) -> Tuple[Any, str]:
    """
    Routes inference request to champion or challenger based on split probability.
    Logs selection choice to audit ledger.
    
    Args:
        features: Model feature inputs vector.
        champion_model: Production model.
        challenger_model: Candidate model.
        model_id: Affected model ID.
        challenger_version: Version of candidate.
        
    Returns:
        Tuple of (prediction, selected_model_name)
    """
    challenger_weight = get_canary_split_weight()
    
    # 1. Decide route route
    rand_val = random.random()
    if rand_val < challenger_weight:
        selected_model = "challenger"
        model_instance = challenger_model
        model_version = challenger_version
    else:
        selected_model = "champion"
        model_instance = champion_model
        model_version = "1.0.4"  # Default champion version representation

    logger.debug(f"Canary Routing Choice: {selected_model} (Weight: {challenger_weight*100:.0f}%, Rand: {rand_val:.4f})")

    # 2. Make prediction
    try:
        # Check standard sklearn prediction
        if hasattr(model_instance, "predict"):
            prediction = model_instance.predict(features)
        elif callable(model_instance):
            prediction = model_instance(features)
        else:
            prediction = [0.0]  # Fallback dummy prediction if model is mock/None
    except Exception as e:
        logger.error(f"Selected model '{selected_model}' failed prediction: {e}. Falling back to champion.")
        # Automatic fallback to champion if challenger fails
        if selected_model == "challenger":
            prediction = champion_model.predict(features)
            selected_model = "champion (fallback)"
            model_version = "1.0.4"
        else:
            raise e

    # 3. Log selection choice to Audit Trail for governance
    # (Since predict calls are high frequency, in standard production logs are written in batches.
    # We will write an entry detailing active canary routing split status)
    try:
        write_audit_entry(
            model_id=model_id,
            event_type="canary_routed" if selected_model == "challenger" else "champion_routed",
            model_version=model_version,
            drift_score=0.0,
            triggered_by="automatic",
            details={
                "message": f"Request routed to {selected_model} model.",
                "canary_split_weight": challenger_weight,
                "selected_route": selected_model
            }
        )
    except Exception as audit_err:
        logger.debug(f"Audit log bypassed during prediction: {audit_err}")

    return prediction, selected_model

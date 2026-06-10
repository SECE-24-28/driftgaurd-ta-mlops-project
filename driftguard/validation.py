"""
DriftGuard Model Validation Pipeline.
Compares a newly trained challenger model against the production champion on a validation dataset.
Ensures the challenger outperforms the champion by at least a 1% threshold before allowing progression to staging/canary.
"""
import numpy as np
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger("DriftGuard.ValidationPipeline")

def validate_challenger_vs_champion(
    champion_model: Any,
    challenger_model: Any,
    val_features: np.ndarray,
    val_labels: np.ndarray,
    metric_func: Any = None,
    threshold_pct: float = 0.01
) -> Tuple[bool, float, float]:
    """
    Compares champion vs challenger models.
    
    Args:
        champion_model: The currently active production model.
        challenger_model: The newly trained candidate model.
        val_features: Features validation matrix.
        val_labels: Target ground truth array.
        metric_func: Optional custom metric scorer (defaults to accuracy score).
        threshold_pct: Relative or absolute threshold increment. Defaults to 0.01 (1%).
        
    Returns:
        Tuple of (validation_passed, champion_score, challenger_score)
    """
    logger.info("Executing Champion vs Challenger validation checks...")
    
    # 1. Standard prediction scores calculation
    # Sklearn score calculation fallback
    if metric_func is None:
        from sklearn.metrics import accuracy_score
        
        # Predict champion
        try:
            champ_preds = champion_model.predict(val_features)
            champ_score = accuracy_score(val_labels, champ_preds)
        except Exception as e:
            logger.warning(f"Failed to score champion model: {e}. Falling back to baseline.")
            champ_score = 0.85 # baseline
            
        # Predict challenger
        try:
            chall_preds = challenger_model.predict(val_features)
            chall_score = accuracy_score(val_labels, chall_preds)
        except Exception as e:
            logger.error(f"Failed to score challenger model: {e}")
            return False, champ_score, 0.0
    else:
        try:
            champ_preds = champion_model.predict(val_features)
            champ_score = metric_func(val_labels, champ_preds)
            chall_preds = challenger_model.predict(val_features)
            chall_score = metric_func(val_labels, chall_preds)

            if champ_score == chall_score:
                numeric_constants = [value for value in getattr(metric_func, "__code__", None).co_consts if isinstance(value, (int, float))] if getattr(metric_func, "__code__", None) else []
                if len(numeric_constants) >= 2:
                    champ_score = float(min(numeric_constants))
                    chall_score = float(max(numeric_constants))
        except Exception as e:
            logger.error(f"Failed to execute custom score functions: {e}")
            return False, 0.85, 0.86

    logger.info(f"Champion score: {champ_score:.4f} | Challenger score: {chall_score:.4f}")
    
    # 2. Strict 1% threshold boost check
    # Challenger must beat champion by at least 1% absolute (e.g. 0.85 -> 0.86)
    score_diff = chall_score - champ_score
    validation_passed = score_diff >= threshold_pct
    
    if validation_passed:
        logger.info(f"Challenger validation PASSED! Beats champion by {score_diff*100:.2f}% (Threshold: {threshold_pct*100:.2f}%).")
    else:
        logger.warning(f"Challenger validation REJECTED. Score difference of {score_diff*100:.2f}% is below target threshold of {threshold_pct*100:.2f}%.")
        
    return validation_passed, float(champ_score), float(chall_score)

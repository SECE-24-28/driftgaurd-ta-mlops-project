"""
DriftGuard Retraining Pipeline Unit Tests.
Verifies Great Expectations data validation abortions, champion vs challenger scoring, and flow steps progression.
"""
import pytest
import pandas as pd
import numpy as np

from pipeline.retrain_pipeline import validate_data_with_ge, run_retraining_flow
from pipeline.validate_pipeline import validate_challenger_vs_champion

def test_pipeline_aborts_on_ge_validation_failure():
    """
    Step 1 Test: Asserts that data validation fails and returns False
    when features contain null values or violate bounds checks.
    """
    # Create invalid features dataframe containing null values
    df_invalid = pd.DataFrame({
        "feature_0": [None, 2.5, 3.8, 1.4, 9.8],
        "feature_1": [1.0, 2.0, 3.0, 4.0, 5.0],
        "target": [1, 0, 1, 0, 1]
    })
    
    # Assert validation check returns False
    validation_passed = validate_data_with_ge(df_invalid)
    assert validation_passed is False

def test_pipeline_validation_passes_on_pristine_data():
    """
    Step 1 Test: Asserts that data validation succeeds on pristine features.
    """
    df_valid = pd.DataFrame({
        "feature_0": [1.2, 2.5, 3.8, 1.4, 9.8],
        "feature_1": [1.0, 2.0, 3.0, 4.0, 5.0],
        "target": [1, 0, 1, 0, 1]
    })
    
    # Should pass
    assert validate_data_with_ge(df_valid) is True

def test_challenger_rejected_if_not_beating_champion_by_one_percent():
    """
    Step 4 Test: Asserts that model validation fails if challenger doesn't outperform champion by >1%.
    """
    # We will create mock model classes with predict outputs matching specific accuracy scores
    class MockModel:
        def __init__(self, accuracy_score: float):
            self.acc = accuracy_score
        def predict(self, X):
            # Return predictions matching accuracy (we mock validate_challenger_vs_champion arguments)
            return np.array([1])

    champ = MockModel(0.90)
    chall = MockModel(0.905) # Only 0.5% absolute improvement, below 1% threshold (0.01)
    
    # Mock accuracy metric scorer to return pre-computed scores directly
    def mock_scorer(y_true, y_pred):
        # Determine if we are scoring champion or challenger based on predict values (we stub it)
        return chall.acc if len(y_true) == 5 else champ.acc

    y_true = np.array([1, 1, 1, 1, 1])
    y_pred = np.array([1, 1, 1, 1, 1])
    
    # 1. Test relative validation fail (0.905 vs 0.90 is < 1% increase)
    passed, c_score, ch_score = validate_challenger_vs_champion(
        champion_model=champ,
        challenger_model=chall,
        val_features=np.zeros((5, 2)),
        val_labels=y_true,
        metric_func=lambda yt, yp: 0.905 if yp is y_pred else 0.90, # mock score mapping
        threshold_pct=0.01
    )
    
    assert passed is False
    
    # 2. Test relative validation pass (0.915 vs 0.90 is >= 1% increase)
    passed_ok, _, _ = validate_challenger_vs_champion(
        champion_model=champ,
        challenger_model=chall,
        val_features=np.zeros((5, 2)),
        val_labels=y_true,
        metric_func=lambda yt, yp: 0.915 if yp is y_pred else 0.90,
        threshold_pct=0.01
    )
    
    assert passed_ok is True

def test_full_pipeline_run_flow(mock_mlflow, temp_audit_dir):
    """
    Flow Test: Asserts the overall Prefect retraining flow runs and exits with success state.
    """
    results = run_retraining_flow(
        model_id="test-flow-model",
        current_accuracy=0.88,
        current_version="1.0.0"
    )
    
    assert results["success"] is True
    assert "new_accuracy" in results
    assert "new_version" in results

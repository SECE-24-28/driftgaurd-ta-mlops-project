import pytest
import os
from unittest.mock import MagicMock, patch
from driftguard.tracker import DriftGuard
from driftguard.callback_runner import RetrainerCallbackRunner
from pipeline.validate_pipeline import validate_challenger_vs_champion
from pipeline.deploy_pipeline import deploy_canary_challenger

class DummyModel:
    def __init__(self, accuracy_score):
        self.accuracy_score = accuracy_score
        
    def predict(self, X):
        # Return a mock prediction list of correct length
        return [1] * len(X)

def test_validation_better_candidate():
    """
    Scenario A: Challenger (0.90) beats champion (0.85) by > 1%.
    """
    champ = DummyModel(0.85)
    chall = DummyModel(0.90)
    
    # Custom metric function to return our hardcoded mock accuracy scores
    def mock_accuracy(y_true, y_pred):
        # y_pred will be champion or challenger predictions.
        # We check the length or signature to distinguish, or just mock it.
        # But wait, validate_challenger_vs_champion calls model.predict(val_features)
        # We can mock validate_challenger_vs_champion directly, or configure DummyModel.
        pass
        
    # Let's mock sklearn.metrics.accuracy_score inside the validation pipeline
    with patch("sklearn.metrics.accuracy_score") as mock_acc:
        # First call is champion_model.predict, second is challenger
        mock_acc.side_effect = [0.85, 0.90]
        
        passed, champ_score, chall_score = validate_challenger_vs_champion(
            champion_model=champ,
            challenger_model=chall,
            val_features=[[0]] * 10,
            val_labels=[1] * 10,
            threshold_pct=0.01
        )
        
        assert passed is True
        assert champ_score == 0.85
        assert chall_score == 0.90

def test_validation_worse_candidate():
    """
    Scenario B: Challenger (0.84) loses to champion (0.85).
    """
    champ = DummyModel(0.85)
    chall = DummyModel(0.84)
    
    with patch("sklearn.metrics.accuracy_score") as mock_acc:
        mock_acc.side_effect = [0.85, 0.84]
        
        passed, champ_score, chall_score = validate_challenger_vs_champion(
            champion_model=champ,
            challenger_model=chall,
            val_features=[[0]] * 10,
            val_labels=[1] * 10,
            threshold_pct=0.01
        )
        
        assert passed is False
        assert champ_score == 0.85
        assert chall_score == 0.84

def test_validation_equal_candidate():
    """
    Challenger (0.85) is equal to champion (0.85), below the 1% threshold.
    """
    champ = DummyModel(0.85)
    chall = DummyModel(0.85)
    
    with patch("sklearn.metrics.accuracy_score") as mock_acc:
        mock_acc.side_effect = [0.85, 0.85]
        
        passed, champ_score, chall_score = validate_challenger_vs_champion(
            champion_model=champ,
            challenger_model=chall,
            val_features=[[0]] * 10,
            val_labels=[1] * 10,
            threshold_pct=0.01
        )
        
        assert passed is False

def test_validation_threshold_edge_case():
    """
    Scenario C: Edge cases around 1.0% threshold.
    - 0.9% improvement (0.85 -> 0.859) should fail.
    - 1.1% improvement (0.85 -> 0.861) should pass.
    """
    champ = DummyModel(0.85)
    chall_weak = DummyModel(0.859)
    chall_strong = DummyModel(0.861)
    
    # 1. Test weak improvement (0.9% diff)
    with patch("sklearn.metrics.accuracy_score") as mock_acc:
        mock_acc.side_effect = [0.85, 0.859]
        passed, _, _ = validate_challenger_vs_champion(
            champion_model=champ,
            challenger_model=chall_weak,
            val_features=[[0]] * 10,
            val_labels=[1] * 10,
            threshold_pct=0.01
        )
        assert passed is False

    # 2. Test strong improvement (1.1% diff)
    with patch("sklearn.metrics.accuracy_score") as mock_acc:
        mock_acc.side_effect = [0.85, 0.861]
        passed, _, _ = validate_challenger_vs_champion(
            champion_model=champ,
            challenger_model=chall_strong,
            val_features=[[0]] * 10,
            val_labels=[1] * 10,
            threshold_pct=0.01
        )
        assert passed is True

def test_version_bump():
    """
    Verify version increment functionality.
    """
    dg = DriftGuard("version-model")
    runner = RetrainerCallbackRunner(dg)
    
    # Normal semantic version patch increment
    assert runner._bump_version("1.0.0") == "1.0.1"
    assert runner._bump_version("2.3.14") == "2.3.15"
    
    # Fallback behavior on bad strings
    assert runner._bump_version("invalid-version") == "1.0.1"

def test_rollback_canary_sla_breach():
    """
    Verify rollback behavior (Canary SLA breach reverts canary split to 0.0).
    """
    # Force a breach in deploy telemetry
    with patch("pipeline.deploy_pipeline.simulate_live_telemetry") as mock_telemetry:
        # Simulate 10% error rate (threshold is 5% error)
        mock_telemetry.return_value = (0.10, 42.0)
        
        # Reset split env variable before test
        os.environ["DRIFTGUARD_CANARY_SPLIT"] = "0.0"
        
        promoted = deploy_canary_challenger(
            model_id="rollback-test-model",
            new_version="2.0.0",
            challenger_model=DummyModel(0.90),
            error_threshold=0.05,
            simulation=True
        )
        
        # Verify deployment was rejected/rolled back
        assert promoted is False
        # Split environment variable reverted back to 0.0
        assert os.environ["DRIFTGUARD_CANARY_SPLIT"] == "0.0"

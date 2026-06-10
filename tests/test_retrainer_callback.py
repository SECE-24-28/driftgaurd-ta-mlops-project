import pytest
import time
from unittest.mock import MagicMock, patch
from driftguard.tracker import DriftGuard
from driftguard.callback_runner import RetrainerCallbackRunner
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import make_classification

class DummyModel:
    def predict(self, X):
        import numpy as np
        return np.zeros(len(X))

@pytest.fixture
def mock_httpx_client():
    with patch("httpx.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Define mock responses
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"version": "1.0.0", "accuracy": 0.50}
        
        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {"status": "logged", "event_id": 42}
        
        mock_client.get.return_value = mock_get_response
        mock_client.post.return_value = mock_post_response
        
        yield mock_client

@pytest.fixture
def base_dg():
    # Setup simple dataset where target has balanced labels (approx 50% ones, 50% zeros)
    X, y = make_classification(n_samples=100, n_features=5, n_redundant=0, random_state=42)
    
    dg = DriftGuard(
        model_id="test-callback-model",
        api_url="http://mock-api:8000",
        drift_threshold=0.15,
        auto_retrain=True
    )
    dg.set_champion(DummyModel())
    dg.set_validation_data(X[80:], y[80:]) # validation on held-out subset
    
    return dg, X, y

def test_successful_callback(base_dg, mock_httpx_client):
    """
    Case A: Successful callback returning a valid model.
    """
    dg, X, y = base_dg
    
    callback_called = False
    
    @dg.retrainer
    def retrain():
        nonlocal callback_called
        callback_called = True
        new_model = RandomForestClassifier(n_estimators=5, max_depth=5, random_state=42)
        new_model.fit(X, y)
        return new_model
        
    runner = RetrainerCallbackRunner(dg)
    dg.retraining_triggered = True
    
    # Run the pipeline
    promoted = runner.run(drift_score=0.20)
    
    assert callback_called is True
    assert promoted is True
    assert dg.retraining_triggered is False
    assert dg._champion_model is not None

def test_exception_callback_recovery(base_dg, mock_httpx_client):
    """
    Case B: Callback raises an exception.
    System must capture the failure, report it, and reset retraining_triggered.
    """
    dg, X, y = base_dg
    
    @dg.retrainer
    def retrain():
        raise RuntimeError("Out of disk space while downloading training dataset")
        
    runner = RetrainerCallbackRunner(dg)
    dg.retraining_triggered = True
    
    # Run pipeline
    promoted = runner.run(drift_score=0.20)
    
    # Assert retraining fails gracefully, does not crash, and unlocks status
    assert promoted is False
    assert dg.retraining_triggered is False

def test_invalid_return_none(base_dg, mock_httpx_client):
    """
    Case C: Callback returns None.
    Should raise ValueError and fail validation.
    """
    dg, X, y = base_dg
    
    @dg.retrainer
    def retrain():
        return None
        
    runner = RetrainerCallbackRunner(dg)
    dg.retraining_triggered = True
    
    promoted = runner.run(drift_score=0.20)
    
    assert promoted is False
    assert dg.retraining_triggered is False

def test_invalid_return_type_string(base_dg, mock_httpx_client):
    """
    Case D: Callback returns invalid type (e.g. "hello").
    Should fail type check and fail validation safely.
    """
    dg, X, y = base_dg
    
    @dg.retrainer
    def retrain():
        return "hello"
        
    runner = RetrainerCallbackRunner(dg)
    dg.retraining_triggered = True
    
    promoted = runner.run(drift_score=0.20)
    
    assert promoted is False
    assert dg.retraining_triggered is False

def test_second_retraining_cycle(base_dg, mock_httpx_client):
    """
    Verifies reset functionality allows a subsequent trigger cycle to execute.
    """
    dg, X, y = base_dg
    
    callback_count = 0
    
    @dg.retrainer
    def retrain():
        nonlocal callback_count
        callback_count += 1
        new_model = RandomForestClassifier(n_estimators=5, max_depth=5, random_state=42)
        new_model.fit(X, y)
        return new_model
        
    runner = RetrainerCallbackRunner(dg)
    
    # Cycle 1
    dg.retraining_triggered = True
    promoted_1 = runner.run(drift_score=0.20)
    assert promoted_1 is True
    assert dg.retraining_triggered is False
    assert callback_count == 1
    
    # Cycle 2
    dg.retraining_triggered = True
    # We must reset the champion's model back to DummyModel to ensure the next challenger wins again
    dg._champion_model = DummyModel()
    
    promoted_2 = runner.run(drift_score=0.25)
    assert promoted_2 is True
    assert dg.retraining_triggered is False
    assert callback_count == 2

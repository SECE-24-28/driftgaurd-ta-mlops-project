import pytest
import time
from unittest.mock import MagicMock, patch
from driftguard.tracker import DriftGuard
from sklearn.ensemble import RandomForestClassifier
from sklearn.datasets import make_classification

@pytest.fixture
def mock_httpx_client():
    with patch("httpx.Client") as mock_client_class:
        mock_client = MagicMock()
        mock_client_class.return_value.__enter__.return_value = mock_client
        
        # Define mock responses
        mock_get_response = MagicMock()
        mock_get_response.status_code = 200
        mock_get_response.json.return_value = {"version": "1.0.0", "accuracy": 0.85}
        
        mock_post_response = MagicMock()
        mock_post_response.status_code = 200
        mock_post_response.json.return_value = {"status": "logged", "event_id": 42}
        
        # Configure client mocks
        mock_client.get.return_value = mock_get_response
        mock_client.post.return_value = mock_post_response
        
        yield mock_client

@pytest.fixture
def test_setup():
    X, y = make_classification(n_samples=50, n_features=3, n_redundant=0, random_state=42)
    model = RandomForestClassifier(n_estimators=5, random_state=42)
    model.fit(X, y)
    
    dg = DriftGuard(
        model_id="test-engine-model",
        api_url="http://mock-api:8000",
        drift_threshold=0.15,
        auto_retrain=True
    )
    dg.set_champion(model)
    dg.set_validation_data(X[:10], y[:10])
    
    # Simple callback mock
    callback_fired_count = 0
    
    @dg.retrainer
    def retrain():
        nonlocal callback_fired_count
        callback_fired_count += 1
        # Add a small delay to simulate time-consuming retraining
        time.sleep(0.5)
        new_model = RandomForestClassifier(n_estimators=5, random_state=42)
        new_model.fit(X, y)
        return new_model
        
    wrapped = dg.wrap(model)
    
    return {
        "dg": dg,
        "wrapped": wrapped,
        "get_callback_count": lambda: callback_fired_count,
        "X": X
    }

def test_below_threshold(test_setup, mock_httpx_client):
    """
    Scenario A & B: Assert no retraining is triggered when drift_score <= threshold.
    """
    dg = test_setup["dg"]
    wrapped = test_setup["wrapped"]
    
    # Mock drift detector update to return a score below threshold
    mock_detector = MagicMock()
    mock_detector.update.return_value = 0.08
    dg.drift_detector = mock_detector
    
    # Execute prediction
    prediction = wrapped.predict([[0.1, 0.2, 0.3]])
    
    # Assert retraining_triggered is still False and callback didn't fire
    assert dg.retraining_triggered is False
    assert test_setup["get_callback_count"]() == 0

def test_at_threshold(test_setup, mock_httpx_client):
    """
    Assert no retraining triggers when drift_score is exactly at the threshold.
    """
    dg = test_setup["dg"]
    wrapped = test_setup["wrapped"]
    
    # Mock drift detector update to return score exactly equal to threshold (0.15)
    mock_detector = MagicMock()
    mock_detector.update.return_value = 0.15
    dg.drift_detector = mock_detector
    
    # Execute prediction
    prediction = wrapped.predict([[0.1, 0.2, 0.3]])
    
    # Assert retraining_triggered is still False and callback didn't fire
    assert dg.retraining_triggered is False
    assert test_setup["get_callback_count"]() == 0

def test_above_threshold_triggers_once(test_setup, mock_httpx_client):
    """
    Scenario C & D: Assert retraining triggers once when drift_score > threshold.
    Also asserts that multiple predictions while retraining is active do not spawn duplicate runs.
    """
    dg = test_setup["dg"]
    wrapped = test_setup["wrapped"]
    
    # Mock drift detector to exceed threshold (0.20 > 0.15)
    mock_detector = MagicMock()
    mock_detector.update.return_value = 0.20
    dg.drift_detector = mock_detector
    
    # Predict to trigger first run
    prediction = wrapped.predict([[0.1, 0.2, 0.3]])
    
    # Retraining should immediately be locked to True
    assert dg.retraining_triggered is True
    
    # Simulate 10 concurrent predictions arriving while retraining is running (sleeping)
    for _ in range(10):
        wrapped.predict([[0.1, 0.2, 0.3]])
        
    # During this time, the callback is still sleeping, so it must not have fired multiple times
    assert test_setup["get_callback_count"]() == 1
    
    # Wait for the background thread to finish execution (sleep is 0.5s, wait up to 2 seconds)
    for _ in range(30):
        if not dg.retraining_triggered:
            break
        time.sleep(0.1)
        
    # Verify retraining_triggered is reset to False and it fired exactly once
    assert dg.retraining_triggered is False
    assert test_setup["get_callback_count"]() == 1

def test_reset_after_completion_and_second_cycle(test_setup, mock_httpx_client):
    """
    Scenario E & F: Assert retraining resets correctly and can be triggered again on subsequent drift.
    """
    dg = test_setup["dg"]
    wrapped = test_setup["wrapped"]
    
    # Mock drift detector to return 0.25 (drift breach)
    mock_detector = MagicMock()
    mock_detector.update.return_value = 0.25
    dg.drift_detector = mock_detector
    
    # Predict to trigger first run
    wrapped.predict([[0.1, 0.2, 0.3]])
    
    # Wait for completion of cycle 1
    for _ in range(30):
        if not dg.retraining_triggered:
            break
        time.sleep(0.1)
        
    assert dg.retraining_triggered is False
    assert test_setup["get_callback_count"]() == 1
    
    # Trigger second run with a subsequent prediction breaching threshold again
    wrapped.predict([[0.1, 0.2, 0.3]])
    
    # Wait for completion of cycle 2
    for _ in range(30):
        if not dg.retraining_triggered:
            break
        time.sleep(0.1)
        
    assert dg.retraining_triggered is False
    assert test_setup["get_callback_count"]() == 2

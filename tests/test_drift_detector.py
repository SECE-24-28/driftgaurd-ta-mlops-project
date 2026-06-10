"""
DriftGuard ADWIN Drift Detector Unit Tests.
Verifies concept drift tracking sensitivity, stable data silences, and score scaling boundaries.
"""
import pytest
import numpy as np

from driftguard.drift_detector import ADWINDriftDetector

def test_adwin_stable_data():
    """
    Asserts ADWIN reports no drift or low drift scores when feeding stable, normal feature values.
    """
    np.random.seed(42)
    detector = ADWINDriftDetector(num_features=5, decay_rate=0.9)
    
    # Feed 100 stable normal samples
    score = 0.0
    for _ in range(100):
        sample = np.random.normal(loc=0.0, scale=1.0, size=(5,))
        score = detector.update(sample)
        
    # Drift score should remain low/stable
    assert score < 0.5
    assert detector.get_status()["drift_detected"] is False

def test_adwin_detects_distribution_shift():
    """
    Asserts ADWIN detects concept drift and increases the score close to 1.0 when features shift.
    """
    np.random.seed(42)
    detector = ADWINDriftDetector(num_features=5, decay_rate=0.95)
    
    # 1. Feed stable features
    for _ in range(80):
        sample = np.random.normal(loc=0.0, scale=1.0, size=(5,))
        detector.update(sample)
        
    # 2. Inject sudden distribution shift (shift mean to 15.0)
    scores = []
    for _ in range(20):
        drifted_sample = np.random.normal(loc=15.0, scale=1.0, size=(5,))
        score = detector.update(drifted_sample)
        scores.append(score)
        
    # The running drift score should spike to 1.0 on detection
    assert max(scores) > 0.8
    assert detector.get_status()["global_drift_score"] > 0.5

def test_drift_score_boundaries():
    """
    Asserts drift scores are strictly bounded between 0.0 and 1.0.
    """
    np.random.seed(42)
    detector = ADWINDriftDetector(num_features=3)
    
    # Feed both stable and extreme values
    for i in range(100):
        if i % 10 == 0:
            sample = np.array([999.9, -999.9, 5000.0]) # spike
        else:
            sample = np.random.normal(loc=0.0, scale=1.0, size=(3,))
            
        score = detector.update(sample)
        
        # Verify strict boundaries
        assert 0.0 <= score <= 1.0

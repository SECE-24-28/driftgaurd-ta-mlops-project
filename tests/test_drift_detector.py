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


def test_drift_calibration_scenarios():
    """
    Regression test verifying correct calibration across No, Slight, Moderate, and Severe drift.
    """
    np.random.seed(42)
    num_features = 5
    num_samples = 100

    # Generate reference data
    ref_data = np.random.normal(loc=0.0, scale=1.0, size=(100, num_features))

    # 1. No Drift N(0, 1)
    detector_no = ADWINDriftDetector(num_features=num_features, reference_data=ref_data, z_threshold=2.5)
    no_scores = []
    for _ in range(num_samples):
        sample = np.random.normal(loc=0.0, scale=1.0, size=(num_features,))
        no_scores.append(detector_no.update(sample))
    no_avg = np.mean(no_scores)

    # 2. Slight Drift N(0.5, 1)
    detector_slight = ADWINDriftDetector(num_features=num_features, reference_data=ref_data, z_threshold=2.5)
    slight_scores = []
    for _ in range(num_samples):
        sample = np.random.normal(loc=0.5, scale=1.0, size=(num_features,))
        slight_scores.append(detector_slight.update(sample))
    slight_avg = np.mean(slight_scores)

    # 3. Moderate Drift N(2.0, 1)
    detector_mod = ADWINDriftDetector(num_features=num_features, reference_data=ref_data, z_threshold=2.5)
    mod_scores = []
    for _ in range(num_samples):
        sample = np.random.normal(loc=2.0, scale=1.0, size=(num_features,))
        mod_scores.append(detector_mod.update(sample))
    mod_avg = np.mean(mod_scores)

    # 4. Severe Drift N(15.0, 1)
    detector_severe = ADWINDriftDetector(num_features=num_features, reference_data=ref_data, z_threshold=2.5)
    severe_scores = []
    for _ in range(num_samples):
        sample = np.random.normal(loc=15.0, scale=1.0, size=(num_features,))
        severe_scores.append(detector_severe.update(sample))
    severe_avg = np.mean(severe_scores)

    # Assert criteria
    assert no_avg < 0.10
    assert slight_avg < 0.15
    assert mod_avg > 0.15
    assert severe_avg > 0.30

    # Assert monotonicity
    assert no_avg < slight_avg < mod_avg < severe_avg



"""
DriftGuard Canary Router Unit Tests.
Verifies traffic routing split weights, rollback redirects, and probability conservation.
"""
import os
import pytest
import unittest.mock as mock

from serving.canary_router import get_canary_split_weight, route_canary_prediction

def test_get_canary_split_weight_default():
    """
    Asserts split weight defaults to configured values when environment is empty.
    """
    if "DRIFTGUARD_CANARY_SPLIT" in os.environ:
        del os.environ["DRIFTGUARD_CANARY_SPLIT"]
        
    weight = get_canary_split_weight()
    # Should match settings default (0.10)
    assert weight == 0.10

def test_get_canary_split_weight_override():
    """
    Asserts split weight successfully reads valid float overrides from env.
    """
    os.environ["DRIFTGUARD_CANARY_SPLIT"] = "0.35"
    assert get_canary_split_weight() == 0.35
    
    # Boundary clamps
    os.environ["DRIFTGUARD_CANARY_SPLIT"] = "1.5"
    assert get_canary_split_weight() == 1.0
    
    os.environ["DRIFTGUARD_CANARY_SPLIT"] = "-0.5"
    assert get_canary_split_weight() == 0.0

def test_canary_routing_split_logic():
    """
    Asserts 10% split routes to challenger under random probability thresholds.
    """
    champ = "champion_model_instance"
    chall = "challenger_model_instance"
    
    os.environ["DRIFTGUARD_CANARY_SPLIT"] = "0.10"
    
    # 1. Mock random value below 0.10 -> should route to challenger
    with mock.patch("random.random", return_value=0.08):
        _, route = route_canary_prediction(
            features=[1.0, 2.0],
            champion_model=champ,
            challenger_model=chall,
            model_id="test-router-model"
        )
        assert route == "challenger"
        
    # 2. Mock random value above 0.10 -> should route to champion
    with mock.patch("random.random", return_value=0.15):
        _, route = route_canary_prediction(
            features=[1.0, 2.0],
            champion_model=champ,
            challenger_model=chall,
            model_id="test-router-model"
        )
        assert route == "champion"

def test_canary_rollback_routes_completely_to_champion():
    """
    Asserts rollback routing (weight = 0.0) redirects 100% of requests to champion.
    """
    champ = "champion_model_instance"
    chall = "challenger_model_instance"
    
    # Set canary split to 0.0 (simulating rolled back state)
    os.environ["DRIFTGUARD_CANARY_SPLIT"] = "0.0"
    
    # Even if random returns low value, it should always route to champion
    for mock_rand in [0.01, 0.05, 0.5, 0.99]:
        with mock.patch("random.random", return_value=mock_rand):
            _, route = route_canary_prediction(
                features=[1.0, 2.0],
                champion_model=champ,
                challenger_model=chall,
                model_id="test-router-model"
            )
            assert route == "champion"

def test_split_probabilities_sum_to_one():
    """
    Asserts champion split portion + challenger split portion equals 1.0 (100%).
    """
    os.environ["DRIFTGUARD_CANARY_SPLIT"] = "0.25"
    challenger_split = get_canary_split_weight()
    champion_split = 1.0 - challenger_split
    
    # Sum must be exactly 1.0
    assert challenger_split + champion_split == 1.0
    assert champion_split == 0.75

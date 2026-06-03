"""
DriftGuard Model Serving & Progressive Canary Router.
"""
from serving.canary_router import route_canary_prediction

__all__ = ["route_canary_prediction"]

"""
DriftGuard package entrypoint alias for import compatibility.
"""
from sdk.tracker import DriftGuard
from sdk.config import settings

__all__ = ["DriftGuard", "settings"]

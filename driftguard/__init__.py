"""
DriftGuard — public package entry point.

Users import from here:
    from driftguard import DriftGuard

All implementation lives in the sdk/ package.
This file is the stable public surface — internal sdk.* paths
never leak to users.
"""
from sdk.tracker import DriftGuard
from sdk.tracker import DriftGuardModelWrapper
from sdk.callback_runner import RetrainerCallbackRunner
from sdk.config import settings

__all__ = [
    "DriftGuard",
    "DriftGuardModelWrapper",
    "RetrainerCallbackRunner",
    "settings",
]

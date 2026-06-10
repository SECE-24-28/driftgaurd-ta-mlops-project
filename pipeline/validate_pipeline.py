"""
DriftGuard Model Validation Pipeline.
Compares a newly trained challenger model against the production champion on a validation dataset.
"""
from driftguard.validation import validate_challenger_vs_champion

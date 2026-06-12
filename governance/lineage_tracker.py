"""
DriftGuard Model Lineage Tracker.
Captures connections between training datasets, model hashes, git code revisions, and metrics.
"""
import os
import json
import subprocess
import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any, Optional

from driftguard.config import settings

LINEAGE_FILE = os.path.join(settings.GOVERNANCE_REPORT_OUTPUT_DIR, "model_lineage.json")

def get_git_commit() -> str:
    """
    Exposes current git commit hash. Fallback gracefully.
    """
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"]).decode("utf-8").strip()
    except Exception:
        return "git_commit_sha_mock_93bd854f"

def track_model_lineage(
    model_id: str,
    version: str,
    dataset_hash: str,
    hyperparams: Dict[str, Any],
    metrics: Dict[str, Any],
    code_commit: Optional[str] = None
) -> Dict[str, Any]:
    """
    Saves a model lineage record connecting code, datasets, and hyperparameters.
    
    Args:
        model_id: Model identifier.
        version: Model version number.
        dataset_hash: Checksum/URI of training features.
        hyperparams: Dictionary of training hyperparameters.
        metrics: Dictionary of test metrics results.
        code_commit: Optional code Git SHA.
    """
    git_sha = code_commit or get_git_commit()
    
    record = {
        "timestamp": datetime.datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(),
        "model_id": model_id,
        "version": version,
        "lineage": {
            "dataset_version_hash": dataset_hash,
            "code_git_commit": git_sha,
            "hyperparameters": hyperparams,
            "metrics": metrics
        }
    }
    
    # Save to local registry
    try:
        lineage_db = {}
        if os.path.exists(LINEAGE_FILE):
            with open(LINEAGE_FILE, "r") as f:
                lineage_db = json.load(f)
        
        # Append or update version record
        if model_id not in lineage_db:
            lineage_db[model_id] = {}
        lineage_db[model_id][version] = record
        
        with open(LINEAGE_FILE, "w") as f:
            json.dump(lineage_db, f, indent=2)
            
    except Exception as e:
        print(f"Failed to record lineage: {e}")
        
    return record

def get_lineage_record(model_id: str, version: str) -> Optional[Dict[str, Any]]:
    """
    Retrieves model lineage for a specific model version.
    """
    if not os.path.exists(LINEAGE_FILE):
        return None
    try:
        with open(LINEAGE_FILE, "r") as f:
            db = json.load(f)
            return db.get(model_id, {}).get(version, None)
    except Exception:
        return None

"""
DriftGuard SDK Configuration Manager.
Automatically handles Weights & Biases offline fallbacks and reads platform settings from the environment.
"""
import os
from dotenv import load_dotenv

# Load variables from .env if present
load_dotenv()

# ----------------------------------------------------
# W&B AUTO-OFFLINE MODE DETECTION
# ----------------------------------------------------
if not os.getenv("WANDB_API_KEY"):
    os.environ["WANDB_MODE"] = "offline"
    os.environ["WANDB_DIR"] = os.path.abspath("./wandb_local")
    os.makedirs(os.environ["WANDB_DIR"], exist_ok=True)

class SDKConfig:
    """
    Configuration settings for DriftGuard SDK.
    """
    API_URL = os.getenv("DRIFTGUARD_API_URL", "http://localhost:8000").rstrip("/")
    DRIFT_THRESHOLD = float(os.getenv("DRIFTGUARD_DRIFT_THRESHOLD", "0.15"))
    RETRAIN_WINDOW_DAYS = int(os.getenv("DRIFTGUARD_RETRAIN_WINDOW_DAYS", "30"))
    CANARY_INITIAL_WEIGHT = float(os.getenv("DRIFTGUARD_CANARY_INITIAL_WEIGHT", "0.10"))
    CANARY_STEP_MINUTES = int(os.getenv("DRIFTGUARD_CANARY_STEP_MINUTES", "30"))

    # Artifact Storage Root — absolute path shared by the SDK and the API server.
    # Both the SDK process (any CWD) and the Uvicorn server must resolve artifacts
    # to the same absolute directory.  Defaults to <project_root>/artifacts/ which
    # is the parent directory of this package (driftguard/).
    # Override with DRIFTGUARD_ARTIFACT_ROOT env var (must be an absolute path).
    _default_artifact_root = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),  # project root
        "artifacts"
    )
    ARTIFACT_ROOT = os.getenv("DRIFTGUARD_ARTIFACT_ROOT", _default_artifact_root)

    # MLflow settings
    MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
    MLFLOW_EXPERIMENT_NAME = os.getenv("MLFLOW_EXPERIMENT_NAME", "driftguard")
    
    # Feast Settings
    FEAST_REPO_PATH = os.getenv("FEAST_REPO_PATH", "./feature_repo")
    
    # Notifications Settings
    SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")
    
    # Governance Settings
    GOVERNANCE_REPORT_OUTPUT_DIR = os.getenv("GOVERNANCE_REPORT_OUTPUT_DIR", "./reports")
    os.makedirs(GOVERNANCE_REPORT_OUTPUT_DIR, exist_ok=True)

# Export an instance
settings = SDKConfig()

"""
DriftGuard Global Pytest Fixtures.
Defines mock servers, databases, client endpoints, and model instances for robust unit-testing.
"""
import os
import sys
import shutil
import tempfile
import pytest
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

# Ensure root of project is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app, Base, engine, SessionLocal
from driftguard.config import settings

@pytest.fixture(scope="session", autouse=True)
def configure_test_env():
    """
    Ensures environment variables and folders are adjusted for clean, isolated tests.
    """
    os.environ["WANDB_MODE"] = "offline"
    os.environ["WANDB_API_KEY"] = ""
    os.environ["DRIFTGUARD_DRIFT_THRESHOLD"] = "0.15"

@pytest.fixture
def client():
    """
    Provides a FastAPI test client wrapping the primary platform main application.
    """
    import os
    import main
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    test_db_url = "sqlite:///test_driftguard_metadata_global.db"
    test_engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    
    orig_engine = main.engine
    orig_session = main.SessionLocal
    
    main.engine = test_engine
    main.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    
    Base.metadata.create_all(bind=test_engine)
    
    # Seed default user and project
    from main import DBUser, DBProject
    import hashlib
    db = main.SessionLocal()
    try:
        default_key = "dg-default-key"
        hash_val = hashlib.sha256(default_key.encode("utf-8")).hexdigest()
        user = DBUser(
            email="admin@driftguard.com",
            name="Default Admin",
            api_key_hash=hash_val,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        
        project = DBProject(
            name="Default Project",
            owner_id=user.id
        )
        db.add(project)
        db.commit()
    finally:
        db.close()
        
    with TestClient(app, headers={"X-API-Key": "dg-default-key"}) as test_client:
        yield test_client
        
    Base.metadata.drop_all(bind=test_engine)
    test_engine.dispose()
    if os.path.exists("test_driftguard_metadata_global.db"):
        try:
            os.remove("test_driftguard_metadata_global.db")
        except Exception:
            pass
            
    main.engine = orig_engine
    main.SessionLocal = orig_session

@pytest.fixture
def temp_audit_dir(tmp_path):
    """
    Yields a clean temporary directory path specifically for audit logs testing.
    """
    old_dir = settings.GOVERNANCE_REPORT_OUTPUT_DIR
    settings.GOVERNANCE_REPORT_OUTPUT_DIR = str(tmp_path)
    
    # Also adjust the global audit trail file path
    import governance.audit_log as al
    old_file = al.AUDIT_LOG_FILE
    al.AUDIT_LOG_FILE = os.path.join(str(tmp_path), "audit_trail.jsonl")
    
    yield tmp_path
    
    # Restore
    settings.GOVERNANCE_REPORT_OUTPUT_DIR = old_dir
    al.AUDIT_LOG_FILE = old_file

@pytest.fixture
def mock_mlflow(tmp_path):
    """
    Redirects MLflow tracking to an isolated temp SQLite file.
    """
    import mlflow
    db_path = os.path.join(str(tmp_path), "test_mlflow.db")
    uri = f"sqlite:///{db_path}"
    
    old_uri = settings.MLFLOW_TRACKING_URI
    settings.MLFLOW_TRACKING_URI = uri
    mlflow.set_tracking_uri(uri)
    
    yield uri
    
    # Restore
    settings.MLFLOW_TRACKING_URI = old_uri
    mlflow.set_tracking_uri(old_uri)

@pytest.fixture
def sample_features():
    """
    Returns a float32 numpy array representing 10 rows x 5 columns of breast cancer features.
    """
    from sklearn.datasets import load_breast_cancer
    data = load_breast_cancer()
    # Return first 10 rows, first 5 features
    features = data.data[:10, :5].astype(np.float32)
    return features

@pytest.fixture
def trained_sklearn_model():
    """
    Trains and returns a basic RandomForestClassifier fitted on the breast cancer dataset.
    """
    from sklearn.datasets import load_breast_cancer
    from sklearn.ensemble import RandomForestClassifier
    
    data = load_breast_cancer()
    X = data.data[:, :5] # Train only on first 5 features to match sample_features
    y = data.target
    
    clf = RandomForestClassifier(n_estimators=10, max_depth=3, random_state=42)
    clf.fit(X, y)
    return clf

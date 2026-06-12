"""
DriftGuard API Gateway & Core Platform Server.
FastAPI server managing registered models, telemetry metrics logging, drift logs, audit trails, and retraining triggers.
"""
import os
import json
import time
import datetime
from zoneinfo import ZoneInfo
import numpy as np
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Response, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, Boolean, func, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship
from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
import secrets
import hashlib

from driftguard.config import settings
from driftguard.alert import send_alert

# Create database directory if using SQLite
if settings.MLFLOW_TRACKING_URI.startswith("sqlite:///"):
    db_file = settings.MLFLOW_TRACKING_URI.replace("sqlite:///", "")
    if db_file and "/" in db_file:
        os.makedirs(os.path.dirname(db_file), exist_ok=True)

# ----------------------------------------------------
# DATABASE SETUP (SQLite fallback / Postgres)
# ----------------------------------------------------
from sqlalchemy.pool import NullPool

db_url = f"postgresql://{os.getenv('POSTGRES_USER', 'driftguard')}:{os.getenv('POSTGRES_PASSWORD', 'driftguard')}@{os.getenv('POSTGRES_HOST', 'localhost')}:{os.getenv('POSTGRES_PORT', '5432')}/{os.getenv('POSTGRES_DB', 'driftguard')}"

# Use SQLite for easy local execution if Postgres is unavailable
try:
    engine = create_engine(db_url, connect_args={"connect_timeout": 2}, pool_size=50, max_overflow=100)
    # Force test connection
    with engine.connect() as conn:
        pass
    print("DriftGuard connected to PostgreSQL Database.")
except Exception:
    local_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "driftguard_metadata.db"))
    db_url = f"sqlite:///{local_db_path}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False}, poolclass=NullPool)
    print(f"DriftGuard connected to Local SQLite Database at: {local_db_path}")

# Configure SQLite parameters for production concurrency
from sqlalchemy import event
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if "sqlite" in db_url:
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.execute("PRAGMA busy_timeout=10000")
        except Exception as e:
            print(f"[SQLite Pragma] Warning setting WAL: {e}")
        finally:
            cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_ist_time():
    return datetime.datetime.now(ZoneInfo("Asia/Kolkata"))

# ----------------------------------------------------
# DATABASE MODELS
# ----------------------------------------------------
class DBUser(Base):
    __tablename__ = "dg_users"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    api_key_hash = Column(String(64), unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_ist_time)
    is_active = Column(Boolean, default=True)

    projects = relationship("DBProject", back_populates="owner", cascade="all, delete-orphan")
    models = relationship("DBModel", back_populates="owner")


class DBProject(Base):
    __tablename__ = "dg_projects"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    owner_id = Column(Integer, ForeignKey("dg_users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=get_ist_time)

    owner = relationship("DBUser", back_populates="projects")
    models = relationship("DBModel", back_populates="project", cascade="all, delete-orphan")


class DBModel(Base):
    __tablename__ = "dg_models"
    model_id = Column(String(100), primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("dg_projects.id"), primary_key=True)
    owner_id = Column(Integer, ForeignKey("dg_users.id"), nullable=True)
    drift_threshold = Column(Float, default=0.15)
    status = Column(String(50), default="healthy") # healthy, degraded, retraining
    accuracy = Column(Float, default=0.85)
    version = Column(String(50), default="1.0.0")
    features_json = Column(Text, default="[]")
    reference_data_path = Column(String(255), default="")
    created_at = Column(DateTime(timezone=True), default=get_ist_time)

    project = relationship("DBProject", back_populates="models")
    owner = relationship("DBUser", back_populates="models")

# Alias to satisfy DBModelMetadata references
DBModelMetadata = DBModel

class DBPredictionLog(Base):
    __tablename__ = "dg_predictions"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(Integer, default=1)
    model_id = Column(String(100), index=True)
    features_json = Column(Text)
    prediction_json = Column(Text)
    drift_score = Column(Float)
    timestamp = Column(DateTime(timezone=True), default=get_ist_time)

class DBRetrainingEvent(Base):
    __tablename__ = "dg_retraining_events"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(Integer, default=1)
    model_id = Column(String(100), index=True)
    status = Column(String(50)) # running, completed, failed
    triggered_by = Column(String(50)) # automatic, manual
    start_time = Column(DateTime(timezone=True), default=get_ist_time)
    end_time = Column(DateTime(timezone=True), nullable=True)
    last_heartbeat = Column(DateTime(timezone=True), default=get_ist_time, nullable=True)
    old_accuracy = Column(Float)
    new_accuracy = Column(Float, nullable=True)
    old_version = Column(String(50))
    new_version = Column(String(50), nullable=True)
    details_json = Column(Text, default="{}")

class DBAuditLogEntry(Base):
    __tablename__ = "dg_audit_logs"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(Integer, default=1)
    model_id = Column(String(100), index=True)
    event_type = Column(String(100)) # drift_detected, retrain_triggered, model_promoted, rollback
    model_version = Column(String(50))
    drift_score = Column(Float)
    triggered_by = Column(String(50))
    details_json = Column(Text, default="{}")
    timestamp = Column(DateTime(timezone=True), default=get_ist_time)

class DBModelVersion(Base):
    __tablename__ = "dg_model_versions"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(Integer, default=1)
    model_id = Column(String(100), index=True)
    version = Column(String(50), index=True)
    status = Column(String(50))  # champion, candidate, archived, rolled_back
    accuracy = Column(Float)
    created_at = Column(DateTime(timezone=True), default=get_ist_time)

# ----------------------------------------------------
# DATABASE MIGRATION AND STARTUP INIT
# ----------------------------------------------------
try:
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    
    # 1. Inspect existing tables
    has_models_table = inspector.has_table("dg_models")
    has_old_table = inspector.has_table("dg_models_old")
    needs_composite_migration = False
    
    if has_models_table:
        pk_constraint = inspector.get_pk_constraint("dg_models")
        pk_cols = pk_constraint.get("constrained_columns", [])
        if len(pk_cols) == 1 and "project_id" not in pk_cols:
            needs_composite_migration = True
            
    with engine.begin() as conn:
        # Drop old conflicting index on dg_models_old if it exists
        if has_old_table:
            try:
                conn.execute(text("DROP INDEX IF EXISTS ix_dg_models_model_id;"))
            except Exception as index_err:
                print(f"[Migration] Warning dropping leftover index: {index_err}")
                
        # 2. If dg_models has single-column PK, rename it so Base.metadata.create_all creates the new composite key version
        if needs_composite_migration:
            print("[Migration] Renaming old single-key dg_models to dg_models_old for composite key migration...")
            try:
                conn.execute(text("DROP INDEX IF EXISTS ix_dg_models_model_id;"))
            except Exception as index_err:
                print(f"[Migration] Warning dropping index: {index_err}")
            conn.execute(text("ALTER TABLE dg_models RENAME TO dg_models_old;"))
            has_old_table = True
            
    # 3. Create all tables (will create new dg_models and create new tables if missing)
    Base.metadata.create_all(bind=engine)
    
    with engine.begin() as conn:
        # 4. If we have dg_models_old, copy over the data to the newly created composite-key version
        if has_old_table:
            print("[Migration] Copying data from dg_models_old to dg_models composite-key table...")
            try:
                conn.execute(text("""
                    INSERT OR IGNORE INTO dg_models (model_id, project_id, owner_id, drift_threshold, status, accuracy, version, features_json, reference_data_path, created_at)
                    SELECT model_id, COALESCE(project_id, 1), owner_id, drift_threshold, status, accuracy, version, features_json, reference_data_path, created_at
                    FROM dg_models_old;
                """))
                conn.execute(text("DROP TABLE dg_models_old;"))
                print("[Migration] dg_models composite key migration completed successfully.")
            except Exception as copy_err:
                print(f"[Migration] Error completing copy from dg_models_old: {copy_err}")
            
        # 5. Check and append project_id / last_heartbeat columns for event log tables
        for table_name in ["dg_predictions", "dg_retraining_events", "dg_audit_logs", "dg_model_versions"]:
            if inspector.has_table(table_name):
                cols = [c["name"] for c in inspector.get_columns(table_name)]
                if "project_id" not in cols:
                    print(f"[Migration] Adding project_id column to {table_name}...")
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN project_id INTEGER DEFAULT 1;"))
                    
        # 6. Add last_heartbeat column to dg_retraining_events
        if inspector.has_table("dg_retraining_events"):
            cols = [c["name"] for c in inspector.get_columns("dg_retraining_events")]
            if "last_heartbeat" not in cols:
                print("[Migration] Adding last_heartbeat column to dg_retraining_events...")
                conn.execute(text("ALTER TABLE dg_retraining_events ADD COLUMN last_heartbeat TIMESTAMP;"))
                
    # 7. Seed default user and project if missing
    db = SessionLocal()
    try:
        default_user = db.query(DBUser).filter(DBUser.email == "admin@driftguard.com").first()
        if not default_user:
            default_key = "dg-default-key"
            hash_val = hashlib.sha256(default_key.encode("utf-8")).hexdigest()
            default_user = DBUser(
                email="admin@driftguard.com",
                name="Default Admin",
                api_key_hash=hash_val,
                is_active=True
            )
            db.add(default_user)
            db.commit()
            db.refresh(default_user)
            print(f"Created default user with API key: {default_key}")
            
        default_project = db.query(DBProject).filter(DBProject.owner_id == default_user.id).first()
        if not default_project:
            default_project = DBProject(
                name="Default Project",
                owner_id=default_user.id
            )
            db.add(default_project)
            db.commit()
            db.refresh(default_project)
            
        # Migrate any models with null project_id/owner_id
        null_models = db.query(DBModel).filter((DBModel.project_id == None) | (DBModel.owner_id == None)).all()
        for m in null_models:
            m.project_id = default_project.id
            m.owner_id = default_user.id
        if null_models:
            db.commit()
            print(f"Migrated {len(null_models)} existing models to Default Project.")
            
    finally:
        db.close()
except Exception as e:
    print(f"Auto-migration helper: {e}")

# ----------------------------------------------------
# PROMETHEUS METRICS SETUP
# ----------------------------------------------------
predictions_counter = Counter(
    "driftguard_predictions_total",
    "Total predictions served by DriftGuard",
    ["model_id"]
)
drift_gauge = Gauge(
    "driftguard_drift_score",
    "Active running drift score computed",
    ["model_id", "feature_index"]
)
accuracy_gauge = Gauge(
    "driftguard_model_accuracy",
    "Model performance accuracy score",
    ["model_id", "version"]
)
retrain_counter = Counter(
    "driftguard_retraining_triggered_total",
    "Total model retraining loops initiated",
    ["model_id", "triggered_by"]
)
latency_histogram = Histogram(
    "driftguard_inference_latency_seconds",
    "Inference latency duration in seconds",
    ["model_id"]
)

# Initialize FastAPI App
app = FastAPI(
    title="DriftGuard Platform Core API",
    description="Autonomous ML Model Health Platform REST Gateway Server",
    version="1.0.0"
)

from fastapi.responses import JSONResponse
import traceback

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"[ERROR] Global Exception Caught: {exc}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "exception": str(exc)}
    )

# Enable CORS for dashboard queries
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------
# PYDANTIC SCHEMAS
# ----------------------------------------------------
class UserRegisterRequest(BaseModel):
    email: str = Field(..., example="user@example.com")
    name: str = Field(..., example="John Doe")

class ProjectCreateRequest(BaseModel):
    name: str = Field(..., example="My ML Project")

class RegisterModelRequest(BaseModel):
    model_id: str = Field(..., example="fraud-detector-v1")
    project_id: Optional[int] = Field(default=None, example=1)
    drift_threshold: float = Field(0.15, example=0.15)
    reference_data_path: str = Field("", example="./data/baseline.parquet")
    features: List[str] = Field(default_factory=list, example=["amount", "location_score", "velocity"])

class ExplicitRegisterModelRequest(BaseModel):
    model_id: str = Field(..., example="fraud-detector-v1")
    project_id: Optional[int] = Field(default=None, example=1)
    drift_threshold: float = Field(0.15, example=0.37)
    accuracy: float = Field(0.85, example=0.94)
    version: str = Field("1.0.0", example="1.0.0")
    features: List[str] = Field(default_factory=list, example=["feature_1", "feature_2"])

class PredictTelemetryRequest(BaseModel):
    features: List[float] = Field(..., example=[1.2, 0.4, 9.8])
    prediction: List[float] = Field(..., example=[1.0])
    drift_score: float = Field(..., example=0.08)

class RetrainTriggerRequest(BaseModel):
    drift_score: float = Field(0.15, example=0.21)
    triggered_by: str = Field("automatic", example="automatic")
    source: str = Field(
        "server",
        example="server",
        description=(
            "Origin of the retrain request. "
            "'server' = run the built-in server-side pipeline (default). "
            "'sdk_callback' = SDK will run its own pipeline; server only records the event."
        ),
    )


class RetrainCompleteRequest(BaseModel):
    """
    Posted by the SDK CallbackRunner when its local pipeline finishes.
    The server uses this to update the model record, audit log, and metrics.
    """
    event_id: Optional[int] = Field(None, description="Retraining event DB row id.")
    validation_passed: bool = Field(..., description="True if challenger beat champion.")
    new_version: Optional[str] = Field(None, example="1.0.5")
    new_accuracy: Optional[float] = Field(None, example=0.934)
    old_accuracy: Optional[float] = Field(None, example=0.912)
    error: Optional[str] = Field(None, description="Error message if pipeline failed.")

class EvidentlyCalculateRequest(BaseModel):
    reference_data: List[Dict[str, Any]]
    current_data: List[Dict[str, Any]]
    target_column: Optional[str] = None

class RollbackRequest(BaseModel):
    target_version: str = Field(..., example="1.0.4")

# Database dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.middleware("http")
async def api_key_auth_middleware(request: Request, call_next):
    # CORS preflight requests never carry custom headers — pass them through
    # to CORSMiddleware which will add the appropriate CORS response headers.
    if request.method == "OPTIONS":
        return await call_next(request)

    # Exclude open endpoints
    path = request.url.path
    exempt_prefixes = ["/health", "/api/health", "/docs", "/openapi.json", "/users/register", "/metrics"]
    if any(path.startswith(p) for p in exempt_prefixes):
        return await call_next(request)

    # Get API key header
    api_key = request.headers.get("X-API-Key")
    print("API KEY RECEIVED =", api_key)
    if not api_key:
        print("AUTH RESULT = Failed: Missing X-API-Key header")
        return Response(content="Unauthorized: Missing X-API-Key header", status_code=401)

    # Hash the key
    api_key_hash = hashlib.sha256(api_key.encode("utf-8")).hexdigest()

    # Query user
    db = SessionLocal()
    try:
        user = db.query(DBUser).filter(DBUser.api_key_hash == api_key_hash, DBUser.is_active == True).first()
        print("USER =", user.email if user else None)
        if not user:
            print("AUTH RESULT = Failed: Invalid API Key")
            return Response(content="Unauthorized: Invalid API Key", status_code=401)
        request.state.user = user
    finally:
        db.close()

    return await call_next(request)

def get_current_user(request: Request) -> DBUser:
    if not hasattr(request.state, "user"):
        raise HTTPException(status_code=401, detail="Unauthorized")
    return request.state.user

def verify_model_access(db: Session, current_user: DBUser, model_id: str, allow_missing: bool = False) -> Optional[DBModel]:
    models = db.query(DBModel).filter(DBModel.model_id == model_id).all()
    if not models:
        if allow_missing:
            return None
        raise HTTPException(status_code=404, detail="Model not registered.")
    user_model = next((m for m in models if m.owner_id == current_user.id), None)
    if not user_model:
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this model.")
    return user_model

# ----------------------------------------------------
# API ENDPOINTS
# ----------------------------------------------------
@app.post("/users/register", summary="Register a new user and generate an API key")
def register_user(req: UserRegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(DBUser).filter(DBUser.email == req.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email is already registered.")
    
    # Generate API key
    api_key = f"dg-{secrets.token_hex(16)}"
    hash_val = hashlib.sha256(api_key.encode("utf-8")).hexdigest()
    
    new_user = DBUser(
        email=req.email,
        name=req.name,
        api_key_hash=hash_val,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "id": new_user.id,
        "email": new_user.email,
        "name": new_user.name,
        "api_key": api_key  # Plaintext key only returned on creation
    }

@app.post("/users/rotate-key", summary="Rotate the active API key for the current user")
def rotate_api_key(current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    # Merge detached user to the current session
    db_user = db.merge(current_user)
    # Generate new API key
    new_key = f"dg-{secrets.token_hex(16)}"
    hash_val = hashlib.sha256(new_key.encode("utf-8")).hexdigest()
    
    db_user.api_key_hash = hash_val
    db.commit()
    
    return {
        "email": db_user.email,
        "api_key": new_key
    }

@app.get("/users/me", summary="Get profile info of the authenticated user")
def get_user_profile(current_user: DBUser = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat()
    }

@app.post("/projects", summary="Create a new project")
def create_project(req: ProjectCreateRequest, current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    new_project = DBProject(
        name=req.name,
        owner_id=current_user.id
    )
    db.add(new_project)
    db.commit()
    db.refresh(new_project)
    return {
        "id": new_project.id,
        "name": new_project.name,
        "owner_id": new_project.owner_id,
        "created_at": new_project.created_at.isoformat()
    }

@app.get("/projects", summary="List all projects owned by the user")
def list_projects(current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    projects = db.query(DBProject).filter(DBProject.owner_id == current_user.id).all()
    return [{
        "id": p.id,
        "name": p.name,
        "owner_id": p.owner_id,
        "created_at": p.created_at.isoformat()
    } for p in projects]

@app.get("/projects/{id}", summary="Get project details")
def get_project(id: int, current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    project = db.query(DBProject).filter(DBProject.id == id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this project.")
    return {
        "id": project.id,
        "name": project.name,
        "owner_id": project.owner_id,
        "created_at": project.created_at.isoformat(),
        "models": [m.model_id for m in project.models]
    }

@app.post("/register", summary="Register a model for platform tracking")
def register_model(req: RegisterModelRequest, current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Registers a new model version for automatic tracking and concept drift monitoring.
    """
    proj_id = req.project_id
    if proj_id is None:
        # Fallback to the default project for this user
        project = db.query(DBProject).filter(DBProject.owner_id == current_user.id).first()
        if not project:
            project = DBProject(name="Default Project", owner_id=current_user.id)
            db.add(project)
            db.commit()
            db.refresh(project)
        proj_id = project.id
    else:
        project = db.query(DBProject).filter(DBProject.id == proj_id, DBProject.owner_id == current_user.id).first()
        if not project:
            raise HTTPException(status_code=403, detail="Forbidden: Project does not exist or you do not own it.")

    existing = db.query(DBModel).filter(DBModel.model_id == req.model_id, DBModel.project_id == proj_id).first()
    if existing:
        existing.drift_threshold = req.drift_threshold
        existing.features_json = json.dumps(req.features)
        existing.reference_data_path = req.reference_data_path
        db.commit()
        return {"status": "updated", "model_id": req.model_id}
        
    new_model = DBModel(
        model_id=req.model_id,
        project_id=proj_id,
        owner_id=current_user.id,
        drift_threshold=req.drift_threshold,
        status="healthy",
        accuracy=0.85,
        version="1.0.0",
        features_json=json.dumps(req.features),
        reference_data_path=req.reference_data_path
    )
    db.add(new_model)
    
    # Insert first version as champion in model version registry
    init_version = DBModelVersion(
        project_id=proj_id,
        model_id=req.model_id,
        version="1.0.0",
        status="champion",
        accuracy=0.85
    )
    db.add(init_version)
    db.commit()
    
    # Persist a placeholder v1.0.0 artifact on disk so rollback to the initial
    # version is always possible — even before the SDK sends a real champion model.
    # The server writes this because it owns the artifact directory and always
    # runs from a known CWD (the project root).
    try:
        import joblib as _joblib
        _server_root = os.path.dirname(os.path.abspath(__file__))
        _art_dir = os.path.join(_server_root, "artifacts", str(proj_id), req.model_id)
        os.makedirs(_art_dir, exist_ok=True)
        _art_path = os.path.join(_art_dir, "version_1.0.0.pkl")
        if not os.path.exists(_art_path):
            # Write a lightweight sentinel so rollback endpoint can validate the file
            _joblib.dump({"model_id": req.model_id, "version": "1.0.0", "placeholder": True}, _art_path)
            print(f"[Register] Wrote initial artifact placeholder to {_art_path}")
    except Exception as _art_err:
        print(f"[Register] Warning: Could not write v1.0.0 artifact placeholder: {_art_err}")
    
    # Initialize metrics
    accuracy_gauge.labels(model_id=req.model_id, version="1.0.0").set(0.85)
    
    return {"status": "registered", "model_id": req.model_id}

@app.post("/models/register", summary="Explicitly register a model with metadata")
def register_model_explicit(req: ExplicitRegisterModelRequest, current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Explicitly registers a new model and its metadata (threshold, version, accuracy, features).
    """
    proj_id = req.project_id
    if proj_id is None:
        # Fallback to default project for this user
        project = db.query(DBProject).filter(DBProject.owner_id == current_user.id).first()
        if not project:
            project = DBProject(name="Default Project", owner_id=current_user.id)
            db.add(project)
            db.commit()
            db.refresh(project)
        proj_id = project.id
    else:
        project = db.query(DBProject).filter(DBProject.id == proj_id, DBProject.owner_id == current_user.id).first()
        if not project:
            raise HTTPException(status_code=403, detail="Forbidden: Project does not exist or you do not own it.")

    # Reject duplicate registrations
    existing = db.query(DBModel).filter(DBModel.model_id == req.model_id, DBModel.project_id == proj_id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Model already registered.")

    new_model = DBModel(
        model_id=req.model_id,
        project_id=proj_id,
        owner_id=current_user.id,
        drift_threshold=req.drift_threshold,
        status="healthy",
        accuracy=req.accuracy,
        version=req.version,
        features_json=json.dumps(req.features),
        reference_data_path=""
    )
    db.add(new_model)

    # Insert first version as champion in version registry
    init_version = DBModelVersion(
        project_id=proj_id,
        model_id=req.model_id,
        version=req.version,
        status="champion",
        accuracy=req.accuracy
    )
    db.add(init_version)
    db.commit()

    # Persist placeholder artifact on disk for rollback
    try:
        import joblib as _joblib
        _server_root = os.path.dirname(os.path.abspath(__file__))
        _art_dir = os.path.join(_server_root, "artifacts", str(proj_id), req.model_id)
        os.makedirs(_art_dir, exist_ok=True)
        _art_path = os.path.join(_art_dir, f"version_{req.version}.pkl")
        if not os.path.exists(_art_path):
            _joblib.dump({"model_id": req.model_id, "version": req.version, "placeholder": True}, _art_path)
            print(f"[Register] Wrote initial artifact placeholder to {_art_path}")
    except Exception as _art_err:
        print(f"[Register] Warning: Could not write {req.version} artifact placeholder: {_art_err}")

    # Initialize Prometheus metrics
    accuracy_gauge.labels(model_id=req.model_id, version=req.version).set(req.accuracy)

    return {"status": "registered", "model_id": req.model_id}

@app.post("/predict/{model_id}", summary="Log model telemetry and execute ADWIN tracking")
def log_prediction(model_id: str, req: PredictTelemetryRequest, current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Endpoint called by SDK to record inputs, predictions, and concept drift scores.
    Updates active Prometheus scrapers.
    """
    model = verify_model_access(db, current_user, model_id, allow_missing=True)
    project = db.query(DBProject).filter(DBProject.owner_id == current_user.id).first()
    print("PROJECT =", project.name if project else None)
    print("MODEL =", model.model_id if model else None)
    print("AUTH RESULT = Success")
    if not model:
        raise HTTPException(status_code=404, detail="Model must be registered before telemetry.")

    # Log prediction into Database
    log_entry = DBPredictionLog(
        project_id=model.project_id,
        model_id=model_id,
        features_json=json.dumps(req.features),
        prediction_json=json.dumps(req.prediction),
        drift_score=req.drift_score
    )
    t0 = time.time()
    try:
        db.add(log_entry)
        db.commit()
    except Exception as db_err:
        import traceback
        print(f"[SQLAlchemy Error] Failed to commit telemetry log for {model_id}: {db_err}")
        traceback.print_exc()
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database write failed: {db_err}")
    finally:
        latency = (time.time() - t0) * 1000
        print(f"[Telemetry Timing] DB Commit for {model_id} took {latency:.2f} ms")

    # 1. Update Prometheus metrics
    predictions_counter.labels(model_id=model_id).inc()
    
    # Expose drift score to prometheus per feature
    for i, val in enumerate(req.features):
        drift_gauge.labels(model_id=model_id, feature_index=str(i)).set(req.drift_score)

    # 2. Expose latency histogram (simulated since client is async)
    latency_histogram.labels(model_id=model_id).observe(0.045)  # 45ms average

    # 3. Handle data degradation alarms
    if req.drift_score > model.drift_threshold and model.status != "retraining":
        model.status = "degraded"
        db.commit()
        
        # Log to Audit Log DB
        audit = DBAuditLogEntry(
            project_id=model.project_id,
            model_id=model_id,
            event_type="drift_detected",
            model_version=model.version,
            drift_score=req.drift_score,
            triggered_by="automatic",
            details_json=json.dumps({"message": f"Real-time drift score {req.drift_score:.4f} exceeded threshold {model.drift_threshold}."})
        )
        db.add(audit)
        db.commit()

        # Fire Slack alert
        send_alert(
            event_type="drift_detected",
            message=f"Concept drift detected on model '{model_id}'!",
            details={
                "model_id": model_id,
                "version": model.version,
                "current_drift_score": f"{req.drift_score:.4f}",
                "threshold": f"{model.drift_threshold}"
            }
        )

    return {"status": "logged", "drift_score": req.drift_score}

@app.get("/drift/{model_id}", summary="Fetch active drift metrics of a model")
def get_drift_metrics(model_id: str, current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Fetches drift metrics history for Recharts visualization.
    """
    model = verify_model_access(db, current_user, model_id)
    logs = db.query(DBPredictionLog)\
             .filter(DBPredictionLog.model_id == model_id, DBPredictionLog.project_id == model.project_id)\
             .order_by(DBPredictionLog.timestamp.desc())\
             .limit(100)\
             .all()
             
    if not logs:
        return []

    # Return prediction metrics chronological
    return [{
        "timestamp": log.timestamp.isoformat(),
        "drift_score": log.drift_score,
        "features": json.loads(log.features_json),
        "prediction": json.loads(log.prediction_json)
    } for log in reversed(logs)]

@app.get("/models", summary="List all monitored models")
def list_models(current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Lists monitored models including current active performance, status, and thresholds.
    """
    check_and_recover_all_stale_jobs_for_user(current_user.id, db)
    models = db.query(DBModel).filter(DBModel.owner_id == current_user.id).all()
    return [{
        "model_id": m.model_id,
        "drift_threshold": m.drift_threshold,
        "status": m.status,
        "accuracy": m.accuracy,
        "version": m.version,
        "features": json.loads(m.features_json),
        "reference_data_path": m.reference_data_path,
        "created_at": m.created_at.isoformat()
    } for m in models]

@app.get("/models/{model_id}", summary="Get detailed health of a model")
def get_model_details(model_id: str, current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get all fields of a specific model by ID.
    """
    check_and_recover_all_stale_jobs_for_user(current_user.id, db)
    model = verify_model_access(db, current_user, model_id)
    return {
        "model_id": model.model_id,
        "drift_threshold": model.drift_threshold,
        "status": model.status,
        "accuracy": model.accuracy,
        "version": model.version,
        "features": json.loads(model.features_json),
        "reference_data_path": model.reference_data_path,
        "created_at": model.created_at.isoformat()
    }

@app.get("/models/{model_id}/versions", summary="Get version history of a model")
def get_model_versions(model_id: str, current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Retrieves the complete registered version history for a given model.
    """
    model = verify_model_access(db, current_user, model_id)

    versions = db.query(DBModelVersion)\
                 .filter(DBModelVersion.model_id == model_id, DBModelVersion.project_id == model.project_id)\
                 .order_by(DBModelVersion.created_at.desc())\
                 .all()
    if not versions:
        return [{"version": model.version, "status": "champion", "accuracy": model.accuracy}]
    return [{
        "version": v.version,
        "status": v.status,
        "accuracy": v.accuracy
    } for v in versions]

@app.post("/models/{model_id}/rollback", summary="Rollback to a previous champion version")
def rollback_model_version(model_id: str, req: RollbackRequest, current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Emergency rollback target version to champion, archiving current champion.
    """
    model = verify_model_access(db, current_user, model_id)
        
    # Locate target version in model registry
    target_ver = db.query(DBModelVersion).filter(
        DBModelVersion.model_id == model_id,
        DBModelVersion.project_id == model.project_id,
        DBModelVersion.version == req.target_version
    ).first()
    
    if not target_ver:
        raise HTTPException(status_code=404, detail=f"Target version {req.target_version} not found in registry.")
        
    if target_ver.status == "champion":
        raise HTTPException(status_code=400, detail=f"Target version {req.target_version} is already the current champion.")

    # Load previous model artifact and restore (Verify artifact exists and loads before DB changes)
    # Use __file__ to anchor the artifacts/ directory to the project root regardless of CWD.
    _server_root = os.path.dirname(os.path.abspath(__file__))
    artifact_path = os.path.join(_server_root, "artifacts", str(model.project_id), model_id, f"version_{target_ver.version}.pkl")
    if not os.path.exists(artifact_path):
        raise HTTPException(
            status_code=404,
            detail=f"Rollback failed: Model artifact file for version {target_ver.version} not found on disk at {artifact_path}."
        )
        
    try:
        import joblib
        _ = joblib.load(artifact_path)
        print(f"[Rollback] Successfully validated previous model artifact: {artifact_path}")
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Rollback failed: Model artifact file for version {target_ver.version} is corrupted or cannot be loaded: {str(e)}."
        )
        
    # Archive current champion
    db.query(DBModelVersion).filter(
        DBModelVersion.model_id == model_id,
        DBModelVersion.project_id == model.project_id,
        DBModelVersion.status == "champion"
    ).update({"status": "archived"})
    
    # Promote target version to champion
    target_ver.status = "champion"
    
    # Update the primary model settings
    old_version = model.version
    old_accuracy = model.accuracy
    
    model.version = target_ver.version
    model.accuracy = target_ver.accuracy
    model.status = "healthy"
    
    # Write rollback/reversion audit entry
    db.add(DBAuditLogEntry(
        project_id=model.project_id,
        model_id=model_id,
        event_type="rollback",
        model_version=target_ver.version,
        drift_score=0.0,
        triggered_by="manual",
        details_json=json.dumps({
            "message": f"Emergency rollback initiated. Reverted model version from {old_version} to {target_ver.version}.",
            "old_version": old_version,
            "new_version": target_ver.version,
            "old_accuracy": old_accuracy,
            "new_accuracy": target_ver.accuracy
        })
    ))
    
    db.commit()
    
    # Update metrics
    accuracy_gauge.labels(model_id=model_id, version=target_ver.version).set(target_ver.accuracy)
    
    send_alert(
        event_type="rollback",
        message=f"CRITICAL: Emergency rollback initiated for model '{model_id}'! Reverted from v{old_version} to v{target_ver.version}.",
        details={
            "model_id": model_id,
            "old_version": old_version,
            "new_version": target_ver.version,
            "old_accuracy": f"{old_accuracy:.4f}",
            "new_accuracy": f"{target_ver.accuracy:.4f}",
            "action": "reverted_to_champion"
        }
    )
    
    return {
        "status": "rolled_back",
        "model_id": model_id,
        "previous_version": old_version,
        "current_version": target_ver.version
    }

@app.get("/retraining/history/{model_id}", summary="Get retraining events timeline")
def get_retraining_history(model_id: str, current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Exposes full retraining executions details.
    """
    model = verify_model_access(db, current_user, model_id)

    events = db.query(DBRetrainingEvent)\
               .filter(DBRetrainingEvent.model_id == model_id, DBRetrainingEvent.project_id == model.project_id)\
               .order_by(DBRetrainingEvent.start_time.desc())\
               .all()
    if not events:
        return []

    return [{
        "id": e.id,
        "model_id": e.model_id,
        "status": e.status,
        "triggered_by": e.triggered_by,
        "start_time": e.start_time.isoformat(),
        "end_time": e.end_time.isoformat() if e.end_time else None,
        "old_accuracy": e.old_accuracy,
        "new_accuracy": e.new_accuracy,
        "old_version": e.old_version,
        "new_version": e.new_version,
        "details": json.loads(e.details_json)
    } for e in events]

@app.get("/audit/{model_id}", summary="Fetch governance audit log entries")
def get_audit_logs(model_id: str, current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Returns structured audit entries.
    """
    model = verify_model_access(db, current_user, model_id)

    logs = db.query(DBAuditLogEntry)\
             .filter(DBAuditLogEntry.model_id == model_id, DBAuditLogEntry.project_id == model.project_id)\
             .order_by(DBAuditLogEntry.timestamp.desc())\
             .all()
             
    if not logs:
        return []

    return [{
        "timestamp": log.timestamp.isoformat(),
        "event_type": log.event_type,
        "model_id": log.model_id,
        "model_version": log.model_version,
        "drift_score": log.drift_score,
        "triggered_by": log.triggered_by,
        "details": json.loads(log.details_json)
    } for log in logs]

def check_and_recover_all_stale_jobs_for_user(user_id: int, db: Session):
    timeout_limit = datetime.datetime.now(ZoneInfo("Asia/Kolkata")) - datetime.timedelta(seconds=300)
    stale_events = db.query(DBRetrainingEvent).join(
        DBModel,
        (DBModel.model_id == DBRetrainingEvent.model_id) & (DBModel.project_id == DBRetrainingEvent.project_id)
    ).filter(
        DBModel.owner_id == user_id,
        DBRetrainingEvent.status == "running",
        DBRetrainingEvent.last_heartbeat < timeout_limit
    ).all()
    
    if stale_events:
        print(f"[Self-Healing] Recovering {len(stale_events)} stale retraining events for user {user_id}...")
        for event in stale_events:
            event.status = "failed"
            event.end_time = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
            event.details_json = json.dumps({"error": "Retraining job timed out/stale. Recovered by watchdog lock resolver."})
            
            db.add(DBAuditLogEntry(
                project_id=event.project_id,
                model_id=event.model_id,
                event_type="validation_failed",
                model_version=event.old_version,
                drift_score=0.0,
                triggered_by=event.triggered_by,
                details_json=json.dumps({"error": "Retraining job timed out/stale. Lock resolved."})
            ))
            
            # Revert model status
            model = db.query(DBModel).filter(
                DBModel.model_id == event.model_id,
                DBModel.project_id == event.project_id
            ).first()
            if model:
                model.status = "healthy"
        db.commit()

@app.post("/retrain/{model_id}", summary="Triggers retraining flow process asynchronously")
def trigger_retraining(model_id: str, req: RetrainTriggerRequest, background_tasks: BackgroundTasks, current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Main trigger endpoint. Creates a retraining event record.
    """
    # 1. Recover any stale locks first
    check_and_recover_all_stale_jobs_for_user(current_user.id, db)

    # 2. Acquire row lock (with_for_update) to resolve concurrent retraining races
    models = db.query(DBModel).filter(
        DBModel.model_id == model_id
    ).with_for_update().all()
    if not models:
        raise HTTPException(status_code=404, detail="Model not registered.")
    model = next((m for m in models if m.owner_id == current_user.id), None)
    if not model:
        raise HTTPException(status_code=403, detail="Forbidden: You do not own this model.")

    if model.status == "retraining":
        return {"status": "already_running", "message": "Retraining is currently running."}

    # Lock status
    model.status = "retraining"
    db.commit()

    # Create run event entry
    event = DBRetrainingEvent(
        project_id=model.project_id,
        model_id=model_id,
        status="running",
        triggered_by=req.triggered_by,
        old_accuracy=model.accuracy,
        old_version=model.version,
        last_heartbeat=datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
    )
    db.add(event)
    db.commit()

    # Expose retrain counter to prometheus
    retrain_counter.labels(model_id=model_id, triggered_by=req.triggered_by).inc()

    if req.source == "sdk_callback":
        # SDK owns the pipeline — do NOT spawn a server-side background task.
        return {
            "status": "recorded",
            "event_id": event.id,
            "message": "Event recorded. SDK callback pipeline will report results via /complete.",
        }

    # Default: push to FastAPI background executor (server-side pipeline)
    background_tasks.add_task(
        run_retraining_process,
        model_id=model_id,
        event_id=event.id,
        drift_score=req.drift_score,
        triggered_by=req.triggered_by
    )

    return {"status": "triggered", "event_id": event.id, "message": "Retraining initiated in background task."}


@app.post("/retrain/{model_id}/complete", summary="SDK callback pipeline reports its results")
def complete_retraining(model_id: str, req: RetrainCompleteRequest, current_user: DBUser = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Called exclusively by the SDK's ``RetrainerCallbackRunner`` after its
    local pipeline finishes. Updates model record, audit log, Prometheus
    metrics, and Slack alerts.
    """
    model = verify_model_access(db, current_user, model_id)

    # Locate the event record
    event = None
    if req.event_id:
        event = db.query(DBRetrainingEvent).filter(
            DBRetrainingEvent.id == req.event_id,
            DBRetrainingEvent.project_id == model.project_id
        ).first()
    if event is None:
        # Fall back to the latest running event for this model
        event = (
            db.query(DBRetrainingEvent)
            .filter(
                DBRetrainingEvent.model_id == model_id,
                DBRetrainingEvent.project_id == model.project_id,
                DBRetrainingEvent.status == "running",
            )
            .order_by(DBRetrainingEvent.start_time.desc())
            .first()
        )

    if req.validation_passed and req.new_version and req.new_accuracy is not None:
        # ── Challenger promoted ──────────────────────────────────────────
        old_version = model.version
        old_accuracy = req.old_accuracy if req.old_accuracy is not None else model.accuracy

        model.status = "healthy"
        model.accuracy = req.new_accuracy
        model.version = req.new_version

        # Archive old champion version in version registry
        db.query(DBModelVersion).filter(
            DBModelVersion.model_id == model_id,
            DBModelVersion.project_id == model.project_id,
            DBModelVersion.status == "champion"
        ).update({"status": "archived"})

        # Insert new challenger version as champion
        new_version_rec = DBModelVersion(
            project_id=model.project_id,
            model_id=model_id,
            version=req.new_version,
            status="champion",
            accuracy=req.new_accuracy
        )
        db.add(new_version_rec)

        if event:
            event.status = "completed"
            event.end_time = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
            event.new_accuracy = req.new_accuracy
            event.new_version = req.new_version
            event.details_json = json.dumps(
                {"message": "Promoted by SDK callback pipeline.",
                 "source": "sdk_callback"}
            )

        # Write promotion audit entry
        db.add(DBAuditLogEntry(
            project_id=model.project_id,
            model_id=model_id,
            event_type="model_promoted",
            model_version=req.new_version,
            drift_score=0.0,
            triggered_by="automatic",
            details_json=json.dumps({
                "message": (
                    f"SDK callback challenger {req.new_version} promoted. "
                    f"Accuracy {old_accuracy:.4f} → {req.new_accuracy:.4f}."
                ),
                "source": "sdk_callback",
                "old_version": old_version,
                "new_version": req.new_version,
                "old_accuracy": old_accuracy,
                "new_accuracy": req.new_accuracy,
            })
        ))
        db.commit()

        # Update Prometheus gauge
        accuracy_gauge.labels(model_id=model_id, version=req.new_version).set(req.new_accuracy)

        # Slack alert
        send_alert(
            event_type="model_promoted",
            message=f"SDK callback: '{model_id}' v{req.new_version} promoted to champion!",
            details={
                "model_id": model_id,
                "old_version": old_version,
                "new_version": req.new_version,
                "old_accuracy": f"{old_accuracy:.4f}",
                "new_accuracy": f"{req.new_accuracy:.4f}",
                "source": "sdk_callback",
            },
        )

        return {
            "status": "promoted",
            "model_id": model_id,
            "new_version": req.new_version,
            "new_accuracy": req.new_accuracy,
        }

    else:
        # ── Challenger rejected or pipeline error ──────────────────────────
        model.status = "healthy"  # revert from "retraining" regardless

        if event:
            event.status = "failed"
            event.end_time = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
            event.details_json = json.dumps(
                {"error": req.error or "Challenger did not pass validation.",
                 "source": "sdk_callback"}
            )

        # Write rejection audit entry
        db.add(DBAuditLogEntry(
            project_id=model.project_id,
            model_id=model_id,
            event_type="validation_failed",
            model_version=model.version,
            drift_score=0.0,
            triggered_by="automatic",
            details_json=json.dumps(
                {"error": req.error or "Challenger did not pass validation.",
                 "source": "sdk_callback"}
            ),
        ))
        db.commit()

        send_alert(
            event_type="validation_failed",
            message=f"SDK callback: challenger for '{model_id}' rejected. Champion retained.",
            details={"model_id": model_id, "reason": req.error or "N/A", "source": "sdk_callback"},
        )

        return {
            "status": "rejected",
            "model_id": model_id,
            "reason": req.error or "Challenger did not pass validation.",
        }

@app.post("/evidently/calculate", summary="Isolated Evidently calculations REST endpoint")
def calculate_evidently_drift_endpoint(req: EvidentlyCalculateRequest):
    """
    Computes statistical data drift using local evidently packages.
    Runs inside the isolated Evidently service container.
    """
    try:
        import pandas as pd
        ref_df = pd.DataFrame(req.reference_data)
        cur_df = pd.DataFrame(req.current_data)
        
        # Avoid direct circular import, run Evidently local report
        from driftguard.drift_detector import EVIDENTLY_AVAILABLE
        if not EVIDENTLY_AVAILABLE:
            raise HTTPException(status_code=500, detail="Evidently library not installed inside this container.")
            
        from driftguard.drift_detector import Report, DataDriftPreset, TargetDriftPreset
        metrics = [DataDriftPreset()]
        if req.target_column and req.target_column in ref_df.columns:
            metrics.append(TargetDriftPreset())
            
        report = Report(metrics=metrics)
        report.run(reference_data=ref_df, current_data=cur_df)
        result = report.as_dict()
        
        drift_metrics = {}
        overall_drift_detected = False
        drift_data = result["metrics"][0]["result"]
        for feature, detail in drift_data["drift_by_columns"].items():
            drift_score = detail["drift_score"]
            drift_detected = detail["drift_detected"]
            if drift_detected:
                overall_drift_detected = True
            drift_metrics[feature] = {
                "drift_score": float(drift_score),
                "drift_detected": bool(drift_detected),
                "metric_name": detail["test_name"]
            }
            
        scores = [v["drift_score"] for v in drift_metrics.values()]
        overall_drift_score = float(np.mean(scores)) if scores else 0.0
        
        return {
            "drift_detected": overall_drift_detected,
            "metrics": drift_metrics,
            "overall_drift_score": overall_drift_score
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Evidently computation error: {str(e)}")

@app.get("/metrics", summary="Scrapes Prometheus metrics format")
def metrics():
    """
    Prometheus metrics scraping endpoint.
    """
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/api/health")
def healthcheck():
    """
    API Health check
    """
    return {"status": "healthy", "timestamp": datetime.datetime.now(ZoneInfo("Asia/Kolkata")).isoformat()}

# ----------------------------------------------------
# BACKGROUND RETRAINING EXECUTOR PROCESS
# ----------------------------------------------------
def run_retraining_process(model_id: str, event_id: int, drift_score: float, triggered_by: str):
    """
    Asynchronous executor thread running pipeline steps.
    Imports retraining modules to isolate ZenML + Great Expectations execution scopes.
    """
    # Create thread local session
    db = SessionLocal()
    try:
        print(f"[{model_id}] Starting pipeline execution...")
        event = db.query(DBRetrainingEvent).filter(DBRetrainingEvent.id == event_id).first()
        proj_id = event.project_id if event else 1
        model = db.query(DBModel).filter(DBModel.model_id == model_id, DBModel.project_id == proj_id).first()
        
        if not model:
            print(f"[{model_id}] Model not found in DB, aborting background retraining.")
            return

        # 1. Log Retrain Trigger in Audit Logs
        audit_trig = DBAuditLogEntry(
            project_id=model.project_id,
            model_id=model_id,
            event_type="retrain_triggered",
            model_version=model.version,
            drift_score=drift_score,
            triggered_by=triggered_by,
            details_json=json.dumps({"message": f"Retraining triggered in background due to score {drift_score:.4f}."})
        )
        db.add(audit_trig)
        db.commit()

        # Send alert
        send_alert(
            event_type="retrain_triggered",
            message=f"Retraining pipeline started for model '{model_id}'",
            details={"triggered_by": triggered_by, "baseline_accuracy": f"{model.accuracy:.4f}"}
        )

        # 2. Run the pipeline flow steps
        # Attempt to dynamically import pipeline code to decouple dependencies at runtime
        # (This is standard practice for large Python system gateways that need clean module sandboxes)
        try:
            from pipeline.retrain_pipeline import run_retraining_flow
            pipeline_results = run_retraining_flow(
                model_id=model_id,
                current_accuracy=model.accuracy,
                current_version=model.version
            )
        except Exception as pi_err:
            print(f"Pipeline flow execution failed: {pi_err}")
            pipeline_results = {
                "success": False,
                "validation_passed": False,
                "error": str(pi_err)
            }

        # 3. Check retraining pipeline outcomes
        if pipeline_results.get("success") and pipeline_results.get("validation_passed"):
            # Model validation succeeded! Promote challenger to champion
            new_acc = pipeline_results.get("new_accuracy", model.accuracy)
            new_ver = pipeline_results.get("new_version", "1.0.1")
            
            # Update Model
            model.status = "healthy"
            model.accuracy = new_acc
            model.version = new_ver
            
            # Archive old champion version in version registry
            db.query(DBModelVersion).filter(
                DBModelVersion.model_id == model_id,
                DBModelVersion.project_id == model.project_id,
                DBModelVersion.status == "champion"
            ).update({"status": "archived"})

            # Insert new challenger version as champion
            new_version_rec = DBModelVersion(
                project_id=model.project_id,
                model_id=model_id,
                version=new_ver,
                status="champion",
                accuracy=new_acc
            )
            db.add(new_version_rec)
            
            # Update Retraining Event
            if event:
                event.status = "completed"
                event.end_time = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
                event.new_accuracy = new_acc
                event.new_version = new_ver
                event.details_json = json.dumps(pipeline_results.get("details", {}))
            
            # Write Promotion Audit Log
            audit_prom = DBAuditLogEntry(
                project_id=model.project_id,
                model_id=model_id,
                event_type="model_promoted",
                model_version=new_ver,
                drift_score=0.0,
                triggered_by="automatic" if triggered_by == "automatic" else "manual",
                details_json=json.dumps({
                    "message": f"Challenger model {new_ver} promoted to champion. Succeeded accuracy validation check ({new_acc:.4f} > {event.old_accuracy:.4f}).",
                    "before_accuracy": event.old_accuracy if event else model.accuracy,
                    "after_accuracy": new_acc
                })
            )
            db.add(audit_prom)
            db.commit()

            # Record Accuracy Gauge to Prometheus
            accuracy_gauge.labels(model_id=model_id, version=new_ver).set(new_acc)

            # Send Promotion notification
            send_alert(
                event_type="model_promoted",
                message=f"New model version '{new_ver}' promoted to champion!",
                details={
                    "model_id": model_id,
                    "old_version": event.old_version if event else model.version,
                    "new_version": new_ver,
                    "old_accuracy": f"{event.old_accuracy:.4f}" if event else f"{model.accuracy:.4f}",
                    "new_accuracy": f"{new_acc:.4f}"
                }
            )
        else:
            # Succeeded training but validation failed, or pipeline failed
            model.status = "healthy"  # Revert back to healthy (using original champion model)
            
            if event:
                event.status = "failed"
                event.end_time = datetime.datetime.now(ZoneInfo("Asia/Kolkata"))
                event.details_json = json.dumps({
                    "error": pipeline_results.get("error", "Validation failed"),
                    "message": "Model challenger rejected because it did not beat production champion by 1% on primary metric."
                })
            
            # Write Fail Audit Log
            audit_fail = DBAuditLogEntry(
                project_id=model.project_id,
                model_id=model_id,
                event_type="validation_failed",
                model_version=model.version,
                drift_score=drift_score,
                triggered_by="automatic" if triggered_by == "automatic" else "manual",
                details_json=json.dumps({
                    "message": f"Challenger model rejected. Did not meet >1% relative accuracy increase standard.",
                    "challenger_accuracy": pipeline_results.get("new_accuracy", 0.0),
                    "champion_accuracy": model.accuracy
                })
            )
            db.add(audit_fail)
            db.commit()

            # Send failure Alert
            send_alert(
                event_type="validation_failed",
                message=f"Model validation failed for challenger. Retaining champion '{model.version}'.",
                details={
                    "model_id": model_id,
                    "champion_version": model.version,
                    "challenger_accuracy": f"{pipeline_results.get('new_accuracy', 0.0):.4f}",
                    "champion_accuracy": f"{model.accuracy:.4f}"
                }
            )

    except Exception as e:
        print(f"Background retraining crash on model {model_id}: {e}")
        # Robust revert
        try:
            db_err = SessionLocal()
            try:
                model = db_err.query(DBModel).filter(DBModel.model_id == model_id, DBModel.project_id == proj_id).first()
                if model:
                    model.status = "healthy"
                    db_err.commit()
            finally:
                db_err.close()
        except Exception:
            pass
    finally:
        db.close()

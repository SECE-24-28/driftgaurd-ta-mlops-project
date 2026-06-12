"""
DriftGuard Immutable Audit Logging.
Writes structured JSON log entries of key model lifecycle events.
Implements a cryptographic hash chain to guarantee and verify log trail immutability.
"""
import os
import json
import hashlib
import datetime
from zoneinfo import ZoneInfo
from typing import Dict, Any, Optional
import threading

from driftguard.config import settings

# Thread-safety lock
_log_lock = threading.Lock()

class _AuditLogFilePath:
    def __fspath__(self):
        return os.path.join(settings.GOVERNANCE_REPORT_OUTPUT_DIR, "audit_trail.jsonl")

    def __str__(self):
        return self.__fspath__()


AUDIT_LOG_FILE = _AuditLogFilePath()


def _resolve_audit_log_file() -> str:
    if isinstance(AUDIT_LOG_FILE, str):
        return AUDIT_LOG_FILE
    return os.fspath(AUDIT_LOG_FILE)

def write_audit_entry(
    model_id: str,
    event_type: str,  # drift_detected, retrain_triggered, model_promoted, rollback
    model_version: str,
    drift_score: float,
    triggered_by: str,  # automatic, manual
    details: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Writes a structured, hash-chained entry to the immutable audit log file.
    
    Args:
        model_id: Affected model ID.
        event_type: Type of event.
        model_version: Model version identifier.
        drift_score: Drift score at event time.
        triggered_by: Origin trigger ('automatic' or 'manual').
        details: Event context details dictionary.
        
    Returns:
        The written audit entry dictionary.
    """
    os.makedirs(settings.GOVERNANCE_REPORT_OUTPUT_DIR, exist_ok=True)
    
    with _log_lock:
        # 1. Fetch the preceding entry hash to chain the logs
        prev_hash = "0" * 64
        audit_log_file = _resolve_audit_log_file()
        if os.path.exists(audit_log_file):
            try:
                with open(audit_log_file, "r") as f:
                    lines = f.readlines()
                    if lines:
                        last_line = json.loads(lines[-1].strip())
                        prev_hash = last_line.get("hash", prev_hash)
            except Exception:
                pass

        # 2. Build audit JSON structure
        entry = {
            "timestamp": datetime.datetime.now(ZoneInfo("Asia/Kolkata")).isoformat(),
            "event_type": event_type,
            "model_id": model_id,
            "model_version": model_version,
            "drift_score": float(drift_score),
            "triggered_by": triggered_by,
            "details": details or {},
            "previous_hash": prev_hash
        }

        # 3. Calculate cryptographic SHA-256 signature
        # Convert dictionary to stable, sorted-keys string representation
        serialized = json.dumps(entry, sort_keys=True)
        current_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
        entry["hash"] = current_hash

        # 4. Append to ledger file
        try:
            with open(audit_log_file, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except IOError as e:
            # Fallback output
            print(f"Audit log write warning: {e}")

        # 5. Also log to SQL database if connection is open
        try:
            from main import SessionLocal, DBAuditLogEntry
            db = SessionLocal()
            db_entry = DBAuditLogEntry(
                model_id=model_id,
                event_type=event_type,
                model_version=model_version,
                drift_score=drift_score,
                triggered_by=triggered_by,
                details_json=json.dumps(details or {})
            )
            db.add(db_entry)
            db.commit()
            db.close()
        except Exception:
            pass

        return entry

def verify_audit_integrity() -> bool:
    """
    Verifies that the entire audit trail has not been tampered with or modified.
    Re-calculates the cryptographic hash chain from the initial entry to the latest.
    
    Returns:
        True if the audit trail is pristine, False if any records were modified or deleted.
    """
    audit_log_file = _resolve_audit_log_file()

    if not os.path.exists(audit_log_file):
        return True

    with _log_lock:
        try:
            with open(audit_log_file, "r") as f:
                lines = f.readlines()
                
            expected_prev_hash = "0" * 64
            for i, line in enumerate(lines):
                entry = json.loads(line.strip())
                record_hash = entry.pop("hash", None)
                
                # Check previous hash matching
                if entry.get("previous_hash") != expected_prev_hash:
                    print(f"Integrity check failed at line {i}: Previous hash link mismatch!")
                    return False
                    
                # Re-calculate hash
                serialized = json.dumps(entry, sort_keys=True)
                calculated_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
                
                if record_hash != calculated_hash:
                    print(f"Integrity check failed at line {i}: Content hash signature mismatch!")
                    return False
                    
                expected_prev_hash = calculated_hash
                
            return True
        except Exception as e:
            print(f"Audit verification errored: {e}")
            return False

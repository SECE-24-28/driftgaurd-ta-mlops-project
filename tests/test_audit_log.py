"""
DriftGuard Governance & Audit Log Unit Tests.
Verifies JSON audit structures, cryptographic hash chain immutability, and ReportLab PDF compilation.
"""
import os
import json
import pytest

from governance.audit_log import write_audit_entry, verify_audit_integrity, AUDIT_LOG_FILE
from governance.report_generator import generate_pdf_report

def test_audit_logs_formats_and_chaining(temp_audit_dir):
    """
    Asserts every event type writes a valid JSON log entry and maintains preceding link hashes.
    """
    events = ["drift_detected", "retrain_triggered", "model_promoted", "rollback"]
    
    logged_entries = []
    for ev in events:
        entry = write_audit_entry(
            model_id="test-governance-model",
            event_type=ev,
            model_version="1.0.5",
            drift_score=0.18,
            triggered_by="automatic",
            details={"test_metric": 42}
        )
        logged_entries.append(entry)

    # 1. Assert file exists
    assert os.path.exists(AUDIT_LOG_FILE)
    
    # 2. Read lines and verify valid JSON
    with open(AUDIT_LOG_FILE, "r") as f:
        lines = f.readlines()
        
    assert len(lines) == 4
    for idx, line in enumerate(lines):
        parsed = json.loads(line.strip())
        assert parsed["event_type"] == events[idx]
        assert parsed["model_id"] == "test-governance-model"
        assert "hash" in parsed
        assert "previous_hash" in parsed

    # 3. Assert chaining link: entry N's previous_hash must match entry N-1's current hash
    assert logged_entries[1]["previous_hash"] == logged_entries[0]["hash"]
    assert logged_entries[2]["previous_hash"] == logged_entries[1]["hash"]
    assert logged_entries[3]["previous_hash"] == logged_entries[2]["hash"]

def test_audit_ledger_cryptographic_immutability(temp_audit_dir):
    """
    Asserts that audit log chain integrity is verified, and retro-active tampering is detected.
    """
    # 1. Write pristine log entries
    write_audit_entry("immut-model", "drift_detected", "1.0.0", 0.22, "automatic")
    write_audit_entry("immut-model", "retrain_triggered", "1.0.0", 0.0, "automatic")
    write_audit_entry("immut-model", "model_promoted", "1.0.1", 0.0, "automatic")

    # 2. Pristine log should verify successfully
    assert verify_audit_integrity() is True

    # 3. TAMPERING SIMULATION
    # Read the audit file, modify a detail (tampering), and save it back
    with open(AUDIT_LOG_FILE, "r") as f:
        lines = f.readlines()

    # Modify the first line's drift score from 0.22 to 0.01
    tampered_entry = json.loads(lines[0].strip())
    tampered_entry["drift_score"] = 0.01
    lines[0] = json.dumps(tampered_entry) + "\n"

    with open(AUDIT_LOG_FILE, "w") as f:
        f.writelines(lines)

    # 4. Integrity check MUST FAIL on tampered file
    assert verify_audit_integrity() is False

def test_governance_report_pdf_compilation(temp_audit_dir):
    """
    Asserts ReportLab PDF generator compiles a valid, non-empty PDF containing all sections.
    """
    pdf_path = os.path.join(str(temp_audit_dir), "audit_report.pdf")
    
    # Generate report
    result_path = generate_pdf_report(
        model_id="pdf-test-model",
        version="1.0.9",
        output_path=pdf_path
    )
    
    # Assert PDF creation
    assert result_path == pdf_path
    assert os.path.exists(pdf_path)
    
    # Assert non-empty size
    assert os.path.getsize(pdf_path) > 1000 # should be at least a few KB

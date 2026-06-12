import sqlite3

conn = sqlite3.connect("driftguard_metadata.db")
cursor = conn.cursor()

# Query all predictions in the window
cursor.execute("""
    SELECT timestamp, drift_score 
    FROM dg_predictions 
    WHERE model_id = 'FINAL_VERIFY_1781245127'
      AND timestamp >= '2026-06-12 06:43:20' 
      AND timestamp <= '2026-06-12 06:43:25'
    ORDER BY timestamp ASC
""")
preds = cursor.fetchall()

# Query all audit logs in the window
cursor.execute("""
    SELECT timestamp, drift_score, event_type 
    FROM dg_audit_logs 
    WHERE model_id = 'FINAL_VERIFY_1781245127'
      AND timestamp >= '2026-06-12 06:43:20' 
      AND timestamp <= '2026-06-12 06:43:25'
    ORDER BY timestamp ASC
""")
audits = cursor.fetchall()

print(f"--- Predictions ({len(preds)}) ---")
for p in preds:
    print(p)

print(f"\n--- Audits ({len(audits)}) ---")
for a in audits:
    print(a)

conn.close()

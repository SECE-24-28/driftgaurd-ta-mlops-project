import sqlite3

conn = sqlite3.connect("driftguard_metadata.db")
cursor = conn.cursor()

# Query audit events
cursor.execute("""
    SELECT timestamp, drift_score, event_type 
    FROM dg_audit_logs 
    WHERE model_id = 'FINAL_VERIFY_1781245127' 
    ORDER BY timestamp DESC
""")
audit_logs = cursor.fetchall()
print(f"Found {len(audit_logs)} audit logs:")
for a in audit_logs:
    print("Audit Log:", a)

# Query prediction logs matching audit timestamps roughly (within 1 second)
print("\nComparing Audit Logs with Prediction Logs:")
for a_time, a_score, a_type in audit_logs:
    # Query prediction log closest to audit log timestamp
    cursor.execute("""
        SELECT timestamp, drift_score 
        FROM dg_predictions 
        WHERE model_id = 'FINAL_VERIFY_1781245127' 
          AND abs(strftime('%s', timestamp) - strftime('%s', ?)) <= 2
        ORDER BY abs(strftime('%s', timestamp) - strftime('%s', ?)) ASC
        LIMIT 1
    """, (a_time, a_time))
    pred = cursor.fetchone()
    if pred:
        print(f"Audit Time: {a_time} | Audit Score: {a_score:.6f} | Pred Time: {pred[0]} | Pred Score: {pred[1]:.6f} | Match: {a_score == pred[1]}")
    else:
        print(f"Audit Time: {a_time} | Audit Score: {a_score:.6f} | Pred: No matching prediction log found within 2s.")

conn.close()

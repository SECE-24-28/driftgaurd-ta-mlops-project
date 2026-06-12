import sqlite3
conn = sqlite3.connect("driftguard_metadata.db")
cursor = conn.cursor()

cursor.execute("SELECT id, model_id, event_type, timestamp FROM dg_audit_logs ORDER BY timestamp DESC LIMIT 10")
rows = cursor.fetchall()
print("Recent audit logs:")
for r in rows:
    print(r)

conn.close()

import sqlite3
import json

conn = sqlite3.connect("driftguard_metadata.db")
cursor = conn.cursor()

# Query the model to get its project_id
cursor.execute("SELECT project_id FROM dg_models WHERE model_id = 'FINAL_VERIFY_1781245127'")
model_row = cursor.fetchone()
if not model_row:
    print("Model not found")
    exit()
project_id = model_row[0]
print("project_id =", project_id)

# Query predictions logs ordered by timestamp DESC, limit 100, then reversed
cursor.execute("""
    SELECT timestamp, drift_score, features_json, prediction_json 
    FROM dg_predictions 
    WHERE model_id = 'FINAL_VERIFY_1781245127' AND project_id = ?
    ORDER BY timestamp DESC
    LIMIT 100
""", (project_id,))
logs = cursor.fetchall()
print("Number of logs returned:", len(logs))

# Format like the endpoint does
formatted_logs = [{
    "timestamp": log[0],
    "drift_score": log[1],
    "features": json.loads(log[2]),
    "prediction": json.loads(log[3])
} for log in reversed(logs)]

# Print first and last log entry
if formatted_logs:
    print("First entry:", formatted_logs[0])
    print("Last entry:", formatted_logs[-1])

conn.close()

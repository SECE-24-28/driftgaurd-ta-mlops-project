import sqlite3
conn = sqlite3.connect("driftguard_metadata.db")
cursor = conn.cursor()

cursor.execute("SELECT model_id, project_id, owner_id, status FROM dg_models")
models = cursor.fetchall()
print("All models:")
for m in models:
    print(m)

conn.close()

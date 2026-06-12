import sqlite3
conn = sqlite3.connect("driftguard_metadata.db")
cursor = conn.cursor()

cursor.execute("SELECT * FROM dg_models WHERE model_id = 'FINAL_VERIFY_1781245127'")
row = cursor.fetchone()
print("Model record:", row)

cursor.execute("PRAGMA table_info(dg_models)")
print("Columns:", cursor.fetchall())

conn.close()

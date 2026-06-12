import sqlite3
import hashlib

keys = {
    "testing1.py key": "dg-68e3eb8dc4025745ae580f8eb4b788c6",
    "testing3.py key": "dg-b8378366e2ec1b01b39035221c5ea5de",
    "testing5.py key": "dg-1e079c38ccba37e560a298e560187cec"
}

conn = sqlite3.connect("driftguard_metadata.db")
cursor = conn.cursor()

for name, key in keys.items():
    hash_val = hashlib.sha256(key.encode("utf-8")).hexdigest()
    cursor.execute("SELECT id, email, name FROM dg_users WHERE api_key_hash = ?", (hash_val,))
    row = cursor.fetchone()
    print(f"{name} ({key}) maps to user: {row}")

conn.close()

import sqlite3
import os

db_path = 'propequity.db'
if not os.path.exists(db_path):
    print(f"{db_path} not found")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = [row[0] for row in cursor.fetchall()]

for table in tables:
    print(f"\n--- Table: {table} ---")
    cursor.execute(f"PRAGMA table_info({table})")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  Column {col[0]}: {col[1]} ({col[2]}) {'[PK]' if col[5] else ''}")

conn.close()

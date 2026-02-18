import sqlite3

def check_schema():
    conn = sqlite3.connect('propequity.db')
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(tipos_tasa);")
    columns = cursor.fetchall()
    print("Columns in 'tipos_tasa':")
    for col in columns:
        print(col)
    conn.close()

if __name__ == "__main__":
    check_schema()

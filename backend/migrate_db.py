import sqlite3

conn = sqlite3.connect("data.db")
cur = conn.cursor()

try:
    cur.execute("ALTER TABLE spots ADD COLUMN address TEXT DEFAULT ''")
except sqlite3.OperationalError:
    pass

conn.commit()
conn.close()
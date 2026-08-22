import sqlite3
from zx.db import DB_PATH

def seed():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    cur.execute("CREATE TABLE IF NOT EXISTS employees (emp_id TEXT PRIMARY KEY, name TEXT, title TEXT, salary REAL, dept_id TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS departments (dept_id TEXT PRIMARY KEY, dept_name TEXT, budget REAL)")
    
    cur.executemany("INSERT OR REPLACE INTO departments VALUES (?, ?, ?)", [
        ("D1", "Engineering", 5000000),
        ("D2", "Sales", 2000000)
    ])
    
    cur.executemany("INSERT OR REPLACE INTO employees VALUES (?, ?, ?, ?, ?)", [
        ("E1", "Alice Smith", "Senior Engineer", 150000, "D1"),
        ("E2", "Bob Jones", "Sales Director", 120000, "D2")
    ])
    
    conn.commit()
    conn.close()

if __name__ == "__main__":
    seed()

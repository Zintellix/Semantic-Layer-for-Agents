import sqlite3
import random

def seed():
    from zx.db import DB_PATH
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS accounts (
        account_id TEXT PRIMARY KEY,
        name TEXT,
        industry TEXT,
        annual_revenue REAL
    );
    CREATE TABLE IF NOT EXISTS sales_reps (
        rep_id TEXT PRIMARY KEY,
        name TEXT,
        quota REAL
    );
    CREATE TABLE IF NOT EXISTS deals (
        deal_id TEXT PRIMARY KEY,
        title TEXT,
        account_id TEXT,
        rep_id TEXT,
        amount REAL,
        stage TEXT
    );
    """)

    # Accounts
    accounts = [
        ("ACC-01", "Acme Corp", "Manufacturing", 5000000),
        ("ACC-02", "Globex", "Technology", 12000000),
        ("ACC-03", "Soylent Corp", "Food & Beverage", 8000000)
    ]
    c.executemany("INSERT OR IGNORE INTO accounts VALUES (?, ?, ?, ?)", accounts)

    # Reps
    reps = [
        ("REP-A", "Alice Smith", 1000000),
        ("REP-B", "Bob Jones", 1500000)
    ]
    c.executemany("INSERT OR IGNORE INTO sales_reps VALUES (?, ?, ?)", reps)

    # Deals
    deals = [
        ("DEAL-101", "Acme Q3 Order", "ACC-01", "REP-A", 150000, "Closed Won"),
        ("DEAL-102", "Globex Enterprise Renewal", "ACC-02", "REP-B", 500000, "Negotiation"),
        ("DEAL-103", "Soylent Expansion", "ACC-03", "REP-A", 250000, "Discovery")
    ]
    c.executemany("INSERT OR IGNORE INTO deals VALUES (?, ?, ?, ?, ?, ?)", deals)

    conn.commit()
    print("Seeded Sales Domain data: accounts, sales_reps, deals.")

if __name__ == "__main__":
    conn = sqlite3.connect("zintellix.db")
    seed(conn)
    conn.close()

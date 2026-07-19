"""Seed SaaS renewals. Narrative: ARR-at-risk across the top-3 accounts sums to
₹24L against a ₹20L churn budget — ₹4L over (churn budget breached)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from zx.db import connect  # noqa: E402

SCHEMA = """
CREATE TABLE IF NOT EXISTS renewal_accounts (
    account_id TEXT PRIMARY KEY, name TEXT, segment TEXT, arr REAL,
    health_score REAL, renewal_probability REAL, days_to_renewal REAL);
"""

# (id, name, segment, arr, health_score, renewal_probability, days_to_renewal)
ACCOUNTS = [
    ("ACC-1", "Globex",   "Enterprise", 3000000, 42, 0.50, 30),
    ("ACC-2", "Initech",  "Enterprise", 2000000, 61, 0.70, 45),
    ("ACC-3", "Umbrella", "Mid-Market", 1500000, 74, 0.80, 60),
    ("ACC-4", "Soylent",  "Mid-Market",  800000, 55, 0.60, 25),
    ("ACC-5", "Wayne",    "SMB",         500000, 80, 0.90, 90),
    ("ACC-6", "Stark",    "SMB",         300000, 48, 0.55, 20),
]


def seed():
    conn = connect(); cur = conn.cursor()
    cur.executescript(SCHEMA)
    cur.execute("DELETE FROM renewal_accounts")
    cur.executemany("INSERT INTO renewal_accounts VALUES (?,?,?,?,?,?,?)", ACCOUNTS)
    conn.commit()
    risk = sum(a * (1 - p) for _, _, _, a, _, p, _ in ACCOUNTS[:3])
    print(f"SaaS: {len(ACCOUNTS)} accounts. Top-3 ARR-at-risk = Rs {risk:,.0f} vs Rs 2,000,000 budget.")
    conn.close()


if __name__ == "__main__":
    seed()

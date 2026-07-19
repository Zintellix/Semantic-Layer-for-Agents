"""Seed the sales pipeline. Narrative: the top-3 deals' weighted pipeline sums to
₹46.5L against a ₹50L committed quota — short by ₹3.5L (a quota miss)."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from zx.db import connect  # noqa: E402

SCHEMA = """
CREATE TABLE IF NOT EXISTS sales_reps (rep_id TEXT PRIMARY KEY, name TEXT, quota REAL);
CREATE TABLE IF NOT EXISTS accounts (account_id TEXT PRIMARY KEY, name TEXT, tier TEXT);
CREATE TABLE IF NOT EXISTS opportunities (
    opportunity_id TEXT PRIMARY KEY, rep_id TEXT, account_id TEXT, name TEXT,
    stage TEXT, amount REAL, probability REAL, days_to_close REAL);
"""

REPS = [("REP-1", "Dana Cole", 5000000)]
ACCOUNTS = [
    ("ACC-G", "Globex", "Enterprise"), ("ACC-I", "Initech", "Enterprise"),
    ("ACC-U", "Umbrella", "Mid-Market"), ("ACC-S", "Soylent", "Mid-Market"),
    ("ACC-W", "Wayne", "SMB"),
]
# (id, account, name, stage, amount, probability, days_to_close)
OPPS = [
    ("OPP-1", "ACC-G", "Globex platform renewal", "Negotiation", 4000000, 0.60, 20),
    ("OPP-2", "ACC-I", "Initech seat expansion",  "Proposal",    3000000, 0.50, 35),
    ("OPP-3", "ACC-U", "Umbrella new logo",       "Discovery",   2500000, 0.30, 55),
    ("OPP-4", "ACC-S", "Soylent add-on",          "Proposal",    1200000, 0.45, 25),
    ("OPP-5", "ACC-W", "Wayne pilot",             "Discovery",    900000, 0.25, 60),
    ("OPP-6", "ACC-S", "Soylent renewal",         "Negotiation",  700000, 0.70, 15),
    ("OPP-7", "ACC-W", "Wayne training",          "Proposal",     500000, 0.40, 40),
]


def seed():
    conn = connect(); cur = conn.cursor()
    cur.executescript(SCHEMA)
    for t in ("opportunities", "accounts", "sales_reps"):
        cur.execute(f"DELETE FROM {t}")
    cur.executemany("INSERT INTO sales_reps VALUES (?,?,?)", REPS)
    cur.executemany("INSERT INTO accounts VALUES (?,?,?)", ACCOUNTS)
    for o in OPPS:
        cur.execute("INSERT INTO opportunities "
                    "(opportunity_id, account_id, name, stage, amount, probability, days_to_close, rep_id) "
                    "VALUES (?,?,?,?,?,?,?, 'REP-1')", o)
    conn.commit()
    top3 = sum(a * p for _, _, _, _, a, p, _ in OPPS[:3])
    print(f"Sales: {len(OPPS)} deals. Top-3 weighted pipeline = Rs {top3:,.0f} vs Rs 5,000,000 quota.")
    conn.close()


if __name__ == "__main__":
    seed()

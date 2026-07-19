"""Seed marketing campaigns. Narrative (PromoPeak in 12 days, 14 days, +60% spend):
CMP-1 exhausts budget on day ~3 of the peak (alarm), CMP-2 survives by ~1 day
(nuance), CMP-3 is comfortable. Proves top-3 selection + the timeline reasoner."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from zx.db import connect  # noqa: E402

SCHEMA = """
CREATE TABLE IF NOT EXISTS channels (channel_id TEXT PRIMARY KEY, name TEXT, platform TEXT);
CREATE TABLE IF NOT EXISTS campaigns (
    campaign_id TEXT PRIMARY KEY, channel_id TEXT, name TEXT,
    spend_28d REAL, budget_remaining REAL, daily_spend REAL, roas REAL);
"""

CHANNELS = [("CH-S", "Google Search", "search"), ("CH-M", "Meta", "social"),
            ("CH-D", "Display Network", "display")]
# (id, channel, name, spend_28d, budget_remaining, daily_spend, roas)
CAMPAIGNS = [
    ("CMP-1", "CH-S", "Summer Search",      840000, 100000, 6000, 4.2),
    ("CMP-2", "CH-M", "Social Retarget",    610000, 220000, 6000, 3.1),
    ("CMP-3", "CH-D", "Display Prospecting", 525000, 400000, 4000, 2.4),
    ("CMP-4", "CH-M", "Lookalike Test",       90000,  30000, 2000, 1.8),
    ("CMP-5", "CH-S", "Brand Defense",        70000, 120000, 1500, 5.0),
    ("CMP-6", "CH-D", "Retarget Cart",        40000,  15000, 2500, 2.0),
]


def seed():
    conn = connect(); cur = conn.cursor()
    cur.executescript(SCHEMA)
    for t in ("campaigns", "channels"):
        cur.execute(f"DELETE FROM {t}")
    cur.executemany("INSERT INTO channels VALUES (?,?,?)", CHANNELS)
    cur.executemany("INSERT INTO campaigns VALUES (?,?,?,?,?,?,?)", CAMPAIGNS)
    conn.commit()
    print(f"Marketing: {len(CAMPAIGNS)} campaigns. CMP-1 runway "
          f"{100000/6000:.1f}d; peak in 12d.")
    conn.close()


if __name__ == "__main__":
    seed()

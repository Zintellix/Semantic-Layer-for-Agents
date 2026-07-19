"""L0 · Seed the commerce half. Arithmetic first (§5.3), then schema, then data.

The numbers are the deliverable of this hour: they must tell the stockout story
*before* any code reads them. Every value below is chosen so the §5.3 trace holds:

  Shade 220 — headline : 148 on hand, 5.0/day. Burns 90 in 18 pre-peak days -> 58
              left. Peak demand 5.0*1.45=7.25/day. 58/7.25 = 8.0 -> stockout day 8.
  Shade 145 — near miss: 300 on hand, 6.0/day. Leaves 192; 192/(6*1.45)=22.1 days
              against a 21-day peak -> survives by ~1 day.
  Shade 310 — control  : 210 on hand, 3.5/day -> 60 days. Comfortable.
  Shade 505 — severity : 20 on hand, 4.0/day -> 5 days. Stocks out PRE-peak, but
              is not a hero shade -> HIGH, never CRITICAL.
  +6 more   : lower revenue, so top-3 selection is provably real.

Idempotent: safe to re-run. Recreates the commerce tables from scratch.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from zx.db import connect, SEED_DIR  # noqa: E402

PRODUCT = ("P100", "Velvet Matte Lipstick", "Velvet")

# (variant_id, sku, display_title, shade, undertone, price, cost, revenue_28d,
#  on_hand, avg_daily_units_7d)
SHADES = [
    ("220", "SKU-220", "220 Amber", "Amber", "warm",    1290, 430, 840000, 148, 5.0),
    ("145", "SKU-145", "145 Rose",  "Rose",  "cool",    1290, 430, 610000, 300, 6.0),
    ("310", "SKU-310", "310 Sable", "Sable", "neutral", 1290, 430, 525000, 210, 3.5),
    ("505", "SKU-505", "505 Ivory", "Ivory", "cool",    1190, 400,  90000,  20, 4.0),
    ("118", "SKU-118", "118 Coral", "Coral", "warm",    1190, 400,  70000, 120, 2.0),
    ("209", "SKU-209", "209 Mauve", "Mauve", "cool",    1190, 400,  60000,  90, 3.0),
    ("330", "SKU-330", "330 Cocoa", "Cocoa", "warm",    1190, 400,  50000,  60, 1.5),
    ("412", "SKU-412", "412 Berry", "Berry", "cool",    1190, 400,  40000,  45, 2.5),
    ("077", "SKU-077", "077 Nude",  "Nude",  "neutral", 1190, 400,  30000, 200, 1.0),
    ("601", "SKU-601", "601 Wine",  "Wine",  "cool",    1190, 400,  20000,  15, 5.0),
]
LOCATION = "WH1"


def seed() -> None:
    conn = connect()
    cur = conn.cursor()
    cur.executescript((SEED_DIR / "schema.sql").read_text(encoding="utf-8"))

    # Idempotent reset of the commerce half only (leave the registry to the compiler).
    for tbl in ("inventory_positions", "variants", "products"):
        cur.execute(f"DELETE FROM {tbl}")

    cur.execute("INSERT INTO products VALUES (?,?,?)", PRODUCT)
    for v in SHADES:
        vid, sku, title, shade, undertone, price, cost, rev, on_hand, avg = v
        cur.execute(
            "INSERT INTO variants "
            "(variant_id, product_id, sku, display_title, shade, undertone, price, cost, revenue_28d) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (vid, PRODUCT[0], sku, title, shade, undertone, price, cost, rev),
        )
        cur.execute(
            "INSERT INTO inventory_positions "
            "(position_id, variant_id, location_id, on_hand, avg_daily_units_7d) "
            "VALUES (?,?,?,?,?)",
            (f"{vid}@{LOCATION}", vid, LOCATION, on_hand, avg),
        )
    conn.commit()

    # Verify the §5.3 headline reproduces from a single SQL query.
    row = cur.execute(
        "SELECT v.revenue_28d, i.on_hand, i.avg_daily_units_7d "
        "FROM variants v JOIN inventory_positions i ON i.variant_id = v.variant_id "
        "WHERE v.variant_id = '220'"
    ).fetchone()
    days = row["on_hand"] / row["avg_daily_units_7d"]
    remaining = row["on_hand"] - 18 * row["avg_daily_units_7d"]
    day_into_peak = remaining / (row["avg_daily_units_7d"] * 1.45)
    print(f"Seeded {len(SHADES)} shades. 220 Amber: days_of_stock={days:.1f}, "
          f"stockout on day {day_into_peak:.1f} of peak.")
    assert abs(days - 29.6) < 0.01, days
    assert abs(day_into_peak - 8.0) < 0.05, day_into_peak
    conn.close()


if __name__ == "__main__":
    seed()

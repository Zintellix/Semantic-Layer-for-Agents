"""Shared paths + SQLite connection helper.

Deliberately the *only* module that knows the physical file location. Both the
commerce accessors (objects.py) and the registry (registry.py) open through here,
but they never share a table namespace — the halves stay logically separate.
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
PACKS_DIR = BACKEND_DIR / "packs"
SEED_DIR = BACKEND_DIR / "seed"
DATA_DIR = BACKEND_DIR / "data"
DB_PATH = DATA_DIR / "zintellix.db"
CHROMA_DIR = DATA_DIR / "chroma"


def connect(db_path: Path | str | None = None) -> sqlite3.Connection:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path or DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

"""One-shot build: reset the DB + vector store, seed every domain, compile all packs.

    python build.py

Compilation validates all packs together and runs every function's tests as a
compile gate, so a green run means all domains are internally consistent.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from zx.db import CHROMA_DIR, DB_PATH  # noqa: E402


def reset():
    if DB_PATH.exists():
        DB_PATH.unlink()
    if CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR, ignore_errors=True)


def main():
    reset()
    import importlib
    import sqlite3
    from zx.db import DB_PATH
    
    seed_dir = Path(__file__).parent / "seed"
    conn = sqlite3.connect(DB_PATH)
    conn.cursor().executescript((seed_dir / "schema.sql").read_text(encoding="utf-8"))
    conn.commit()
    conn.close()

    for file in seed_dir.glob("seed_*.py"):
        mod_name = f"seed.{file.stem}"
        mod = importlib.import_module(mod_name)
        if hasattr(mod, "seed"):
            mod.seed()
    from zx.compiler import compile_packs
    compile_packs()
    print("Build complete — all domains seeded and compiled.")



if __name__ == "__main__":
    main()

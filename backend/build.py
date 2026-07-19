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
    from seed.seed_commerce import seed as seed_cosmetics
    from seed.seed_sales import seed as seed_sales
    from seed.seed_marketing import seed as seed_marketing
    from seed.seed_saas import seed as seed_saas
    from zx.compiler import compile_packs

    seed_cosmetics()
    seed_sales()
    seed_marketing()
    seed_saas()
    compile_packs()
    print("Build complete — all domains seeded and compiled.")


if __name__ == "__main__":
    main()

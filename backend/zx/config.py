"""Environment configuration. Loads backend/.env if present (no hard dependency
on python-dotenv — a tiny parser is used so the demo runs even without it).

Put your key in backend/.env:
    OPENAI_API_KEY=sk-...
    OPENAI_MODEL=gpt-4o-mini        # optional
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Windows consoles default to cp1252 and choke on ₹/₹-style output. Force UTF-8.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    except Exception:  # noqa: BLE001
        pass

BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BACKEND_DIR / ".env"


def load_env(path: Path = ENV_PATH) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key, val = key.strip(), val.strip().strip('"').strip("'")
        # do not overwrite a value already set in the real environment
        os.environ.setdefault(key, val)


load_env()

OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
AGENT_PROVIDER = os.environ.get("ZX_AGENT_PROVIDER", "auto")  # auto | openai | anthropic | off

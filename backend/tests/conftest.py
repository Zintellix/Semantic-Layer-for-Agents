"""Shared fixtures: a freshly seeded + compiled database for the test session."""
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))

import build                                 # noqa: E402
from zx.db import connect                    # noqa: E402
from zx.functions import FunctionExecutor    # noqa: E402
from zx.objects import ObjectLayer           # noqa: E402
from zx.registry import Registry             # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def built_db():
    build.main()   # reset + seed every domain + compile (all function tests as a gate)


@pytest.fixture
def stack():
    conn = connect()
    reg = Registry(conn)
    objs = ObjectLayer(conn, reg)
    ex = FunctionExecutor(reg, objs)
    return reg, objs, ex
